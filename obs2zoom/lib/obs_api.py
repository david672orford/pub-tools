# Used instead of obs_ws.py when we are running as an OBS script

import obspython as obs
from threading import Condition
import logging

logger = logging.getLogger(__name__)

class ObsEventReader:
	def __init__(self):
		self.on_frontend_event_wrapped = lambda event: self.on_frontend_event(event)
		self.on_source_create_wrapped = lambda data: self.on_source_create(obs.calldata_source(data,"source"))
		self.on_source_destroy_wrapped = lambda data: self.on_source_destroy(obs.calldata_source(data,"source"))
		self.on_media_started_wrapped = lambda event: self.on_media_started(event)
		self.on_media_ended_wrapped = lambda event: self.on_media_ended(event)
		self.queue = []
		self.condition = Condition()
		self.signal_handlers_installed = False

	def startup(self):
		obs.obs_frontend_add_event_callback(self.on_frontend_event_wrapped)

		source_list = obs.obs_enum_sources()
		for source in source_list:
			self.on_source_create(source)
		obs.source_list_release(source_list)

		sh = obs.obs_get_signal_handler()
		obs.signal_handler_connect(sh, "source_create", self.on_source_create_wrapped)
		obs.signal_handler_connect(sh, "source_destroy", self.on_source_destroy_wrapped)

		self.signal_handlers_installed = True

	def shutdown(self):
		if self.signal_handlers_installed:

			obs.obs_frontend_remove_event_callback(self.on_frontend_event_wrapped)

			source_list = obs.obs_enum_sources()
			for source in source_list:
				self.on_source_destroy(source)
			obs.source_list_release(source_list)

			sh = obs.obs_get_signal_handler()
			obs.signal_handler_disconnect(sh, "source_create", self.on_source_create_wrapped)
			obs.signal_handler_disconnect(sh, "source_destroy", self.on_source_destroy_wrapped)

			self.signal_handlers_installed = False

		self.enqueue_message({'update-type': 'Exiting'})

	def send_message(self, data):
		assert data['request-type'] == 'PlayPauseMedia'
		source_name = data['sourceName']
		play_pause = data['playPause']
		source = obs.obs_get_source_by_name(source_name)
		obs.obs_source_media_play_pause(source, play_pause)

	def recv_message(self):
		self.condition.acquire()
		while len(self.queue) == 0:
			self.condition.wait()
		item = self.queue.pop(0)
		self.condition.release()
		return item

	def enqueue_message(self, message):
		self.condition.acquire()
		self.queue.append(message)
		self.condition.notify()
		self.condition.release()

	def get_virtualcam_active(self):
		return obs.obs_frontend_virtualcam_active()

	def get_current_sources(self):
		scene = obs.obs_frontend_get_current_scene()
		return self.get_scene_items(scene)

	def on_frontend_event(self, event):
		if event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED:
			scene = obs.obs_frontend_get_current_scene()
			self.enqueue_message({
				'update-type': 'SwitchScenes',
				'scene-name': obs.obs_source_get_name(scene),
				'sources': self.get_scene_items(scene),
				})
		elif event == obs.OBS_FRONTEND_EVENT_VIRTUALCAM_STARTED:
			self.enqueue_message({ 'update-type': 'VirtualCamStarted' })
		elif event == obs.OBS_FRONTEND_EVENT_VIRTUALCAM_STOPPED:
			self.enqueue_message({ 'update-type': 'VirtualCamStopped' })

	def on_source_create(self, source):
		logger.debug("Source create: %s", obs.obs_source_get_name(source))
		handler = obs.obs_source_get_signal_handler(source)
		obs.signal_handler_connect(handler, "media_started", self.on_media_started_wrapped)
		obs.signal_handler_connect(handler, "media_ended", self.on_media_ended_wrapped)

	def on_source_destroy(self, source):
		logger.debug("Source destroy: %s", obs.obs_source_get_name(source))
		handler = obs.obs_source_get_signal_handler(source)
		obs.signal_handler_disconnect(handler, "media_started", self.on_media_started_wrapped)
		obs.signal_handler_disconnect(handler, "media_ended", self.on_media_ended_wrapped)

	def on_media_started(self, data):
		source = obs.calldata_source(data, "source")
		self.enqueue_message({
			'update-type': 'MediaStarted',
			'sourceName': obs.obs_source_get_name(source),
			})

	def on_media_ended(self, data):
		source = obs.calldata_source(data, "source")
		self.enqueue_message({
			'update-type': 'MediaEnded',
			'sourceName': obs.obs_source_get_name(source),
			})

	def get_scene_items(self, scene):
		scene_items = obs.obs_scene_enum_items(obs.obs_scene_from_source(scene))
		response = []
		for scene_item in scene_items:
			source = obs.obs_sceneitem_get_source(scene_item)
			response.append({
				'name': obs.obs_source_get_name(source),
				'id': obs.obs_sceneitem_get_id(scene_item),
				'type': obs.obs_source_get_id(source),
				})
		obs.sceneitem_list_release(scene_items)
		return response

