import obspython as obs
from subprocess import run

playing_sources = set()

def script_description():
	return "Automatically mute microphone when a video is playing. Unmute and return to first scene when it stops."

def script_load(settings):
	print("script_load")

	source_list = obs.obs_enum_sources()
	for source in source_list:
		self.on_source_create(source)
	obs.source_list_release(source_list)	

	sh = obs.obs_get_signal_handler()
	obs.signal_handler_connect(sh, "source_create", on_source_create_wrapper)
	obs.signal_handler_connect(sh, "source_destroy", on_source_destroy_wrapper)

def script_unload():
	return
	sh = obs.obs_get_signal_handler()
	obs.signal_handler_disconnect(sh, "source_create", on_source_create_wrapper)
	obs.signal_handler_disconnect(sh, "source_destroy", on_source_destroy_wrapper)

	source_list = obs.obs_enum_sources()
	for source in source_list:
		on_source_destroy(source)
	obs.source_list_release(source_list)

def on_source_create_wrapper(data):
	on_source_create(obs.calldata_source(data, "source"))
def on_source_create(source):
	if obs.obs_source_get_id(source) == "ffmpeg_source":
		handler = obs.obs_source_get_signal_handler(source)
		obs.signal_handler_connect(handler, "media_started", on_media_started)
		obs.signal_handler_connect(handler, "media_ended", on_media_ended)

def on_source_destroy_wrapper(data):
	on_source_destroy(obs.calldata_source(data, "source"))
def on_source_destroy(source):
	if obs.obs_source_get_id(source) == "ffmpeg_source":
		handler = obs.obs_source_get_signal_handler(source)
		obs.signal_handler_disconnect(handler, "media_started", on_media_started)
		obs.signal_handler_disconnect(handler, "media_ended", on_media_ended)
		source_name = obs.obs_source_get_name(source)
		if source_name in playing_sources:
			playing_sources.remove(source_name)

def on_media_started(data):
	source = obs.calldata_source(data, "source")
	source_name = obs.obs_source_get_name(source)
	print("media started:", source_name)
	playing_sources.add(source_name)
	print("playing_sources:", playing_sources)
	if len(playing_sources) == 1:
		obs.timer_add(video_start, 100)

def on_media_ended(data):
	source = obs.calldata_source(data, "source")
	source_name = obs.obs_source_get_name(source)
	print("media ended:", source_name)
	playing_sources.remove(source_name)
	print("playing_sources:", playing_sources)
	if len(playing_sources) == 0:
		obs.timer_add(video_end, 100)

def video_start():
	print("video start")
	set_mute(True)
	obs.remove_current_callback()

def video_end():
	print("video end")
	set_mute(False)
	return_to_stage()
	obs.remove_current_callback()

def set_mute(mute):
	run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])

# This needs to be called from a timer. When we call it from a source event the GUI locks up.
def return_to_stage():
	scenelist = obs.obs_frontend_get_scenes()
	#for scene in scenelist:
	#	print("Scene:", obs.obs_source_get_name(scene))
	obs.obs_frontend_set_current_scene(scenelist[0])
	obs.source_list_release(scenelist)

