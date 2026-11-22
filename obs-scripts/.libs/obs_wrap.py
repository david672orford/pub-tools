from collections import defaultdict
from contextlib import contextmanager
import inspect
import json
import obspython as obs

# Monkey patch obspython to prevent lockups
from ctypes import CDLL, c_void_p
from ctypes.util import find_library
def wrap_obs_frontend_set_current_scene():
	frontend = CDLL(find_library("obs-frontend-api"))
	frontend.obs_frontend_set_current_scene.argtypes = [c_void_p]
	frontend.obs_frontend_set_current_scene.restype = None
	def obs_frontend_set_current_scene(scene):
		frontend.obs_frontend_set_current_scene(int(scene))
	return obs_frontend_set_current_scene
obs.obs_frontend_set_current_scene = wrap_obs_frontend_set_current_scene()

class ObsWidget:
	"""Representation of a GUI widget on the script's configuration screen"""
	def __init__(self, type, name, display_name, value=None, min=None, max=None, step=1, default_value=None, options=None, callback=None):
		self.type = type
		self.name = name
		self.display_name = display_name
		self.value = value
		self.min = min
		self.max = max
		self.step = step
		self.default_value = default_value
		self.options = options
		self.callback = callback

class ObsSettings:
	"""Wrapper for an OBS settings object"""

	def __str__(self):
		return str(self.__dict__)

class ObsScene:
	"""Wrapper for an OBS scene object"""

	def __init__(self, scene):
		self.scene = scene

	@property
	def name(self):
		"""Name of scene as seen by user"""
		return obs.obs_source_get_name(self.scene)

class ObsSource:
	"""Wrapper for an OBS source object"""

	def __init__(self, source):
		self.source = obs.calldata_source(source, "source")

	@property
	def id(self):
		"""The source type such as 'source_ffmpeg' or 'source_vlc'"""
		return obs.obs_source_get_id(self.source)

	@property
	def uuid(self):
		"""Unique ID"""
		return obs.obs_source_get_uuid(self.source)

	@property
	def name(self):
		"""The name of the source as seen by the user"""
		return obs.obs_source_get_name(self.source)

	@property
	def signal_handler(self):
		"""An object to which we attach signal handlers to this source"""
		return obs.obs_source_get_signal_handler(self.source)

	@property
	def settings(self):
		raw_settings = obs.obs_source_get_settings(self.source)
		json_text = obs.obs_data_get_json(raw_settings)
		settings = json.loads(json_text)
		obs.obs_data_release(raw_settings)
		return settings

	@property
	def duration(self):
		"""Duration of recording in milliseconds"""
		return obs.obs_source_media_get_duration(self.source)

	@property
	def time(self):
		"""Playhead position in milliseconds from the start"""
		return obs.obs_source_media_get_time(self.source)

	def stop(self):
		"""Halt playback"""
		obs.obs_source_media_stop(self.source)

	def __str__(self):
		return f"<ObsSource id={self.id} name={repr(self.name)} uuid={self.uuid}>"

@contextmanager
def freeing(source_list):
	"""For iterating the scene and source lists"""
	try:
		yield source_list
	finally:
		obs.source_list_release(source_list)

class ObsFrontendEvents:
	"""Frontend events handler shared by all of the khplayer-*.py scripts"""
	# See https://github.com/obsproject/obs-studio/issues/3385
	def __init__(self):
		self.subscriptions = []
		def handler(event):
			#print(f"#### EVENT {event} ####")
			for callback in self.subscriptions:
				callback(event)
		self.handler = handler
		#self.pause_count = 1
		#self.unpause()
		obs.obs_frontend_add_event_callback(self.handler)

	def subscribe(self, callback):
		self.subscriptions.append(callback)

	#def pause(self):
	#	print(f"#### PAUSE {self.pause_count} ####")
	#	assert self.pause_count >= 0
	#	self.pause_count += 1
	#	if self.pause_count == 1:
	#		print("#### REMOVING HANDLER ####")
	#		obs.obs_frontend_remove_event_callback(self.handler)

	#def unpause(self):
	#	print(f"#### UNPAUSE {self.pause_count} ####")
	#	assert self.pause_count > 0
	#	self.pause_count -= 1
	#	if self.pause_count == 0:
	#		print("#### INSTALLING HANDLER ####")
	#		obs.obs_frontend_add_event_callback(self.handler)

frontend_events = ObsFrontendEvents()

class ObsScript:
	"""Derive your OBS script class from this"""
	gui = []

	def __init__(self, debug:bool=False):
		self.debug:bool = debug
		self._install_callbacks(inspect.currentframe().f_back.f_globals)
		self.finished_loading = False
		self._deferred_on_gui_change = None
		self.frontend_events = frontend_events

	#===================================================================
	# Here we install functions for all of the OBS callbacks. Don't
	# override these, override the more pythonic callback we call from
	# these. They are defined below with "on_" prefixes.
	#
	# The documentation is not very clear as to what all these
	# callbacks are for or when they are called. This is what
	# observed in OBS Studio 29.1.3.
	#
	# Script Add Call Sequence:
	# 1) script_defaults()
	# 2) script_load()
	# 3) script_update()
	# 4) script_properties()
	# 5) script_properties()		# Yes, twice!
	# 6) script_update()
	#
	# Script Startup Call Sequence
	# 1) script_defaults()
	# 2) script_load()
	# 3) script_update()
	#
	# Call Sequence when Script's Properties Screen is opened
	# 1) script_properties()
	# 2) script_update()
	#
	# Shutdown Call Sequence
	# 1) script_save()
	# 2) script_unload()
	#
	# Reload Call Sequence
	# 1) script_unload()
	# 2) script_defaults()
	# 3) script_load()
	# 4) script_update()
	#
	# Script Delete Call Sequence
	# 1) script_unload()
	#
	#===================================================================

	# Install OBS callback functions in the global namespace of the calling module
	def _install_callbacks(self, g):
		g["script_description"] = lambda: self.__doc__
		g["script_load"] = lambda settings: self._script_load(settings)
		g["script_unload"] = lambda: self._script_unload()
		g["script_save"] = lambda settings: self._script_save(settings)
		g["script_defaults"] = lambda settings: self._script_defaults(settings)
		g["script_properties"] = lambda: self._script_properties()
		g["script_update"] = lambda settings: self._script_update(settings)

	# Turn the C settings list into an array of ObsSetting objects
	def _pythonize_settings(self, raw_settings):
		settings = ObsSettings()
		for widget in self.gui:
			if widget.type == "bool":
				setattr(settings, widget.name, obs.obs_data_get_bool(raw_settings, widget.name))
			elif widget.type == "int":
				setattr(settings, widget.name, obs.obs_data_get_int(raw_settings, widget.name))
			elif widget.type == "float":
				setattr(settings, widget.name, obs.obs_data_get_double(raw_settings, widget.name))
			elif widget.type in ("text", "select"):
				setattr(settings, widget.name, obs.obs_data_get_string(raw_settings, widget.name).strip())
			elif widget.type != "button":
				raise AssertionError("Undefined widget type: %s" % widget.type)
		return settings

	# Apply values to the raw settings for each widget which has a 'value' attribute
	def _apply_widget_values(self, raw_settings):
		for widget in self.gui:
			value = widget.value
			if value is not None:
				if hasattr(value, "__call__"):
					value = value()
				if widget.type == "bool":
					obs.obs_data_set_bool(raw_settings, widget.name, value)
				elif widget.type == "int":
					obs.obs_data_set_int(raw_settings, widget.name, value)
				elif widget.type == "float":
					obs.obs_data_set_double(raw_settings, widget.name, value)
				elif widget.type in ("text", "select"):
					obs.obs_data_set_string(raw_settings, widget.name, value)
				elif widget.type != "button":
					raise AssertionError("Undefined widget type: %s" % widget.type)

	# Load default settings
	def _script_defaults(self, raw_settings):
		self.raw_settings = raw_settings
		if self.debug:
			print("obs_wrap: script_defaults()")
		for widget in self.gui:
			if widget.type == "bool":
				obs.obs_data_set_default_bool(raw_settings, widget.name, widget.default_value)
			elif widget.type == "int":
				obs.obs_data_set_default_int(raw_settings, widget.name, widget.default_value)
			elif widget.type == "float":
				obs.obs_data_set_default_double(raw_settings, widget.name, widget.default_value)
			elif widget.type in ("text", "select"):
				obs.obs_data_set_default_string(raw_settings, widget.name, widget.default_value)
			elif widget.type != "button":
				raise AssertionError("Undefined widget type: %s" % widget.type)

	def _script_load(self, raw_settings):
		if self.debug:
			print("obs_wrap: script_load()")

		self.on_load(self._pythonize_settings(raw_settings))

		def on_frontend_event(event):
			if self.debug:
				print("obs_wrap: Frontend event:", {
					obs.OBS_FRONTEND_EVENT_STREAMING_STARTING: "STREAMING_STARTING",
					obs.OBS_FRONTEND_EVENT_STREAMING_STARTED: "STREAMING_STARTED",
					obs.OBS_FRONTEND_EVENT_STREAMING_STOPPING: "STREAMING_STOPPING",
					obs.OBS_FRONTEND_EVENT_STREAMING_STOPPED: "STREAMING_STOPPED",
					obs.OBS_FRONTEND_EVENT_RECORDING_STARTING: "RECORDING_STARTING",
					obs.OBS_FRONTEND_EVENT_RECORDING_STARTED: "RECORDING_STARTED",
					obs.OBS_FRONTEND_EVENT_RECORDING_STOPPING: "RECORDING_STOPPING",
					obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED: "RECORDING_STOPPED",
					obs.OBS_FRONTEND_EVENT_SCENE_CHANGED: "SCENE_CHANGED",
					obs.OBS_FRONTEND_EVENT_SCENE_LIST_CHANGED: "SCENE_LIST_CHANGED",
					obs.OBS_FRONTEND_EVENT_TRANSITION_CHANGED: "TRANSITION_CHANGED",
					obs.OBS_FRONTEND_EVENT_TRANSITION_STOPPED: "TRANSITION_STOPPED",
					obs.OBS_FRONTEND_EVENT_TRANSITION_LIST_CHANGED: "TRANSITION_LIST_CHANGED",
					obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_CHANGED: "SCENE_COLLECTION_CHANGED",
					obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_LIST_CHANGED: "SCENE_COLLECTION_LIST_CHANGED",
					obs.OBS_FRONTEND_EVENT_PROFILE_CHANGED: "PROFILE_CHANGED",
					obs.OBS_FRONTEND_EVENT_PROFILE_LIST_CHANGED: "PROFILE_LIST_CHANGED",
					obs.OBS_FRONTEND_EVENT_EXIT: "EXIT",
					obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTING: "REPLAY_BUFFER_STARTING",
					obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STARTED: "REPLAY_BUFFER_STARTED",
					obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPING: "REPLAY_BUFFER_STOPPING",
					obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_STOPPED: "REPLAY_BUFFER_STOPPED",
					obs.OBS_FRONTEND_EVENT_STUDIO_MODE_ENABLED: "STUDIO_MODE_ENABLED",
					obs.OBS_FRONTEND_EVENT_STUDIO_MODE_DISABLED: "STUDIO_MODE_DISABLED",
					obs.OBS_FRONTEND_EVENT_PREVIEW_SCENE_CHANGED: "PREVIEW_SCENE_CHANGED",
					obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_CLEANUP: "SCENE_COLLECTION_CLEANUP",
					obs.OBS_FRONTEND_EVENT_FINISHED_LOADING: "FINISHED_LOADING",
					obs.OBS_FRONTEND_EVENT_RECORDING_PAUSED: "RECORDING_PAUSED",
					obs.OBS_FRONTEND_EVENT_RECORDING_UNPAUSED: "RECORDING_UNPAUSED",
					obs.OBS_FRONTEND_EVENT_TRANSITION_DURATION_CHANGED: "TRANSITION_DURATION_CHANGED",
					obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED: "REPLAY_BUFFER_SAVED",
					obs.OBS_FRONTEND_EVENT_VIRTUALCAM_STARTED: "VIRTUALCAM_STARTED",
					obs.OBS_FRONTEND_EVENT_VIRTUALCAM_STOPPED: "VIRTUALCAM_STOPPED",
					obs.OBS_FRONTEND_EVENT_TBAR_VALUE_CHANGED: "TBAR_VALUE_CHANGED",
					obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_CHANGING: "SCENE_COLLECTION_CHANGING",
					obs.OBS_FRONTEND_EVENT_PROFILE_CHANGING: "PROFILE_CHANGING",
					obs.OBS_FRONTEND_EVENT_SCRIPTING_SHUTDOWN: "SCRIPTING_SHUTDOWN",
					obs.OBS_FRONTEND_EVENT_PROFILE_RENAMED: "PROFILE_RENAMED",
					obs.OBS_FRONTEND_EVENT_SCENE_COLLECTION_RENAMED: "SCENE_COLLECTION_RENAMED",
					obs.OBS_FRONTEND_EVENT_THEME_CHANGED: "THEME_CHANGED",
					obs.OBS_FRONTEND_EVENT_SCREENSHOT_TAKEN: "SCREENSHOT_TAKEN",
					obs.OBS_FRONTEND_EVENT_CANVAS_ADDED: "CANVAS_ADDED",
					obs.OBS_FRONTEND_EVENT_CANVAS_REMOVED: "CANVAS_REMOVED",
					obs.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVING: "REPLAY_BUFFER_SAVING",
					}.get(event, event))
			match event:
				case obs.OBS_FRONTEND_EVENT_FINISHED_LOADING:
					self.finished_loading = True
					# If script_update() was called before this event, there will be settings in
					# self._deferred_on_gui_change. Dispatch then using self.on_gui_change().
					if self._deferred_on_gui_change is not None:
						self.on_gui_change(self._deferred_on_gui_change)
						self._deferred_on_gui_change = None
					self.on_finished_loading()
				case obs.OBS_FRONTEND_EVENT_THEME_CHANGED:
					self.on_theme_changed()
		self.frontend_events.subscribe(on_frontend_event)

	# Called just before settings screen is displayed to build the GUI
	def _script_properties(self):	# why not settings?
		if self.debug:
			print("obs_wrap: script_properties()")
		if not self.finished_loading:
			if self.debug:
				print("obs_wrap: First load or reload, setting finished_loading")
			self.finished_loading = True
		self.on_before_gui()
		self._apply_widget_values(self.raw_settings)
		props = obs.obs_properties_create()
		for widget in self.gui:
			if widget.type == "bool":		# checkbox
				obs.obs_properties_add_bool(props, widget.name, widget.display_name)
			elif widget.type == "int":
				obs.obs_properties_add_int(props, widget.name, widget.display_name, widget.min, widget.max, widget.step)
			elif widget.type == "float":
				obs.obs_properties_add_float(props, widget.name, widget.display_name, widget.min, widget.max, widget.step)
			elif widget.type == "text":		# single line of text
				obs.obs_properties_add_text(props, widget.name, widget.display_name, obs.OBS_TEXT_DEFAULT)
			elif widget.type == "select":	# select box
				select = obs.obs_properties_add_list(props, widget.name, widget.display_name, obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
				options = widget.options
				if hasattr(options, "__call__"):
					options = options()
				for value, description in options:
					obs.obs_property_list_add_string(select, description, value)
			elif widget.type == "button":	# pushbutton
				obs.obs_properties_add_button(props, widget.name, widget.display_name, lambda a, b: widget.callback())
			else:
				raise AssertionError("Undefined widget type: %s" % widget.type)
		return props

	# Apply settings. Called at startup and whenever the user changes settings thereafter.
	# Bundle them into an object and call on_settings().
	def _script_update(self, raw_settings):
		if self.debug:
			print("obs_wrap: script_update()")
		settings = self._pythonize_settings(raw_settings)
		if self.debug:
			print("obs_wrap: settings:", settings)
		if self.finished_loading:
			self.on_gui_change(settings)
		else:
			self._deferred_on_gui_change = settings

	# Called just before script_unload()
	# Documentation is a bit unclear about this, but it sounds like it
	# gives the script an opportunity to stash things in the settings object.
	def _script_save(self, settings):
		if self.debug:
			print("obs_wrap: script_save()")
		#self.on_save()

	# OBS is about to shut down
	def _script_unload(self):
		if self.debug:
			print("obs_wrap: script_unload()")
		self.on_unload()

	#===================================================================
	# Override these as needed in derived classes
	#===================================================================

	def on_load(self, settings):
		pass

	def on_unload(self):
		pass

	def on_before_gui(self):
		pass

	def on_gui_change(self, settings):
		pass

	def on_finished_loading(self):
		pass

	def on_theme_changed(self):
		pass

	#===================================================================
	# Call these as needed from derived classes
	#===================================================================

	def get_scene(self):
		scene = obs.obs_frontend_get_current_scene()
		name = obs.obs_source_get_name(scene)
		obs.obs_source_release(scene)
		return name

	def set_scene(self, scene_name:str):
		if self.debug:
			print("set_scene:", scene_name)
		for scene in self.iter_scenes():
			if scene.name == scene_name:
				#self.frontend_events.pause()
				obs.obs_frontend_set_current_scene(scene.scene)
				#self.frontend_events.unpause()
				break

	def iter_scenes(self):
		with freeing(obs.obs_frontend_get_scenes()) as scene_list:
			for scene in scene_list:
				yield ObsScene(scene)

	def iter_sources(self):
		with freeing(obs.obs_enum_sources()) as source_list:
			for source in source_list:
				yield ObsSource(source)

	def enqueue(self, funct):
		def funct_wrapper():
			obs.remove_current_callback()
			funct()
		obs.timer_add(funct_wrapper, 100)

#=============================================================================
# This mixin simplifies listening for media source events. To use it, include
# it as a parent class and override one or more of the on_* methods.
#
# Media event sequences as observed in OBS 3.1:
# * Uninterrupted from start to finish: source_activate, media_started, media_ended
# * Pause button: media_pause
# * Play button: media_started, media_play
# * Stop button: media_stopped
# * Switch to other scene: source_deactivate, media_ended
#=============================================================================

class ObsScriptSourceEventsMixin:
	def _script_load(self, settings):
		super()._script_load(settings)
		sh = obs.obs_get_signal_handler()
		obs.signal_handler_connect(sh, "source_create", lambda source: self._on_source_create(source))
		obs.signal_handler_connect(sh, "source_destroy", lambda source: self._on_source_destroy(source))

	def _on_source_create(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: source_created:", source)
		self._install_source_listeners(source)
		self.on_source_create(source)

	def _on_source_destroy(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: source_destroy:", source)
		self.on_source_destroy(source)

	def _install_source_listeners(self, source):
		if source.id == "scene":
			handler = source.signal_handler
			obs.signal_handler_connect(handler, "activate", lambda source: self._on_scene_activate(source))
			obs.signal_handler_connect(handler, "deactivate", lambda source: self._on_scene_deactivate(source))
		elif source.id in ("ffmpeg_source", "vlc_source"):
			handler = source.signal_handler
			obs.signal_handler_connect(handler, "activate", lambda source: self._on_source_activate(source))
			obs.signal_handler_connect(handler, "deactivate", lambda source: self._on_source_deactivate(source))
			obs.signal_handler_connect(handler, "media_started", lambda source: self._on_media_started(source))
			obs.signal_handler_connect(handler, "media_ended", lambda source: self._on_media_ended(source))
			obs.signal_handler_connect(handler, "media_pause", lambda source: self._on_media_pause(source))
			obs.signal_handler_connect(handler, "media_play", lambda source: self._on_media_play(source))
			obs.signal_handler_connect(handler, "media_stopped", lambda source: self._on_media_stopped(source))

	def _on_scene_activate(self, source):
		source = obs.calldata_source(source, "source")
		scene_name = obs.obs_source_get_name(source)
		if self.debug:
			print("obs_wrap: scene activated:", scene_name)
		self.on_scene_activate(scene_name)

	def _on_scene_deactivate(self, source):
		source = obs.calldata_source(source, "source")
		scene_name = obs.obs_source_get_name(source)
		if self.debug:
			print("obs_wrap: scene deactivated:", scene_name)
		self.on_scene_deactivate(scene_name)

	def _on_source_activate(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: source_activate:", source)
		self.on_source_activate(source)

	def _on_source_deactivate(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: source_deactivate:", source)
		self.on_source_deactivate(source)

	def _on_media_started(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: media_started:", source)
		self.on_media_started(source)

	def _on_media_ended(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: media_ended:", source)
		self.on_media_ended(source)

	def _on_media_pause(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: media_pause:", source)
		self.on_media_pause(source)

	def _on_media_play(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: media_play:", source)
		self.on_media_play(source)

	def _on_media_stopped(self, source):
		source = ObsSource(source)
		if self.debug:
			print("obs_wrap: media_stopped:", source)
		self.on_media_stopped(source)

	def on_source_create(self, source):
		pass

	def on_source_destroy(self, source):
		pass

	def on_scene_activate(self, scene_name):
		pass

	def on_scene_deactivate(self, scene_name):
		pass

	def on_source_activate(self, source):
		pass

	def on_source_deactivate(self, source):
		pass

	def on_media_started(self, source):
		pass

	def on_media_ended(self, source):
		pass

	def on_media_pause(self, source):
		pass

	def on_media_play(self, source):
		pass

	def on_media_restart(self, source):
		pass

	def on_media_stopped(self, source):
		pass
