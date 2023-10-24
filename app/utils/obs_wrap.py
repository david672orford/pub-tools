import obspython as obs
import inspect
from contextlib import contextmanager

class ObsSetting:
	def __init__(self, type, name, display_name, default_value, **kwargs):
		self.type = type
		self.name = name
		self.display_name = display_name
		self.default_value = default_value
		self.kwargs = kwargs

class ObsScene:
	def __init__(self, scene):
		self.scene = scene
	@property
	def name(self):
		return obs.obs_source_get_name(self.scene)

class ObsSource:
	def __init__(self, source):
		self.source = source
	@property
	def id(self):
		return obs.obs_source_get_id(self.source)
	@property
	def name(self):
		return obs.obs_source_get_name(self.source)
	@property
	def signal_handler(self):
		return obs.obs_source_get_signal_handler(self.source)

@contextmanager
def freeing(source_list):
	try:
		yield source_list
	finally:
		obs.source_list_release(source_list)	

class ObsScript:
	description = "Description of script here"
	settings = []

	def __init__(self):
		# Install OBS callback functions in the global namespace of the calling module
		g = inspect.currentframe().f_back.f_globals
		g['script_description'] = lambda: self.description
		g['script_load'] = lambda settings: self.script_load(settings)
		g['script_unload'] = lambda: self.script_unload()
		g['script_save'] = lambda settings: self.script_save(settings)
		g['script_defaults'] = lambda settings: self.script_defaults(settings)
		g['script_properties'] = lambda: self.script_properties()
		g['script_update'] = lambda settings: self.script_update(settings)

	# Script Startup Sequence
	# 1) script_defaults
	# 2) script_load
	# 3) script_update
	#
	# Properties Screen Sequence
	# 1) script_properties
	# 2) script_update
	#
	# Shutdown Sequence
	# 1) script_save
	# 2) script_unload
	#
	# Reload Sequence
	# 1) script_unload
	# 2) 

	def script_load(self, settings):
		#print("*** script_load()")
		self.on_load()

	def script_unload(self):
		#print("*** script_unload()")
		self.on_unload()

	def script_save(self, settings):
		#print("*** script_save()")
		pass

	# Settings screen defaults
	def script_defaults(self, settings):
		#print("*** script_defaults()")
		for setting in self.settings:
			if setting.type in ("text", "select"):
				obs.obs_data_set_default_string(settings, setting.name, setting.default_value)

	# Create settings GUI
	def script_properties(self):
		#print("*** script_properties()")
		for setting in self.settings:
			if setting.type == "text":
				pass
			elif setting.type == "select":
				pass

	# Accept settings (possibly changed)
	def script_update(self, settings):
		#print("*** script_update()")
		for setting in self.settings:
			pass

	def set_scene(self, scene_name):
		for scene in self.iter_scenes():
			if scene.name == scene_name:
				obs.obs_frontend_set_current_scene(scene.scene)
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
			funct()
			obs.remove_current_callback()
		obs.timer_add(funct_wrapper, 100)

	def on_load(self):
		pass

	def on_unload(self):
		pass

class ObsScriptSourceEventsMixin:
	def script_load(self, settings):
		super().script_load(settings)

		sh = obs.obs_get_signal_handler()
		obs.signal_handler_connect(sh, "source_create", lambda source: self._on_source_create(source))
		obs.signal_handler_connect(sh, "source_destroy", lambda source: self._on_source_destroy(source))

	def _on_source_create(self, source):
		source = obs.calldata_source(source, "source")
		self._install_source_listeners(source)
		self.on_source_create(ObsSource(source))

	def _on_source_destroy(self, source):
		source = obs.calldata_source(source, "source")
		self.on_source_destroy(ObsSource(source))

	def _install_source_listeners(self, source):
		#print("new source:", obs.obs_source_get_id(source), obs.obs_source_get_name(source))
		if obs.obs_source_get_id(source) == "ffmpeg_source":
			handler = obs.obs_source_get_signal_handler(source)
			obs.signal_handler_connect(handler, "media_started", lambda source: self._on_media_started(source))
			obs.signal_handler_connect(handler, "media_ended", lambda source: self._on_media_ended(source))
			obs.signal_handler_connect(handler, "media_pause", lambda source: self._on_media_pause(source))
			obs.signal_handler_connect(handler, "media_play", lambda source: self._on_media_play(source))
			obs.signal_handler_connect(handler, "media_stopped", lambda source: self._on_media_stopped(source))

	# Media event sequences:
	# Uninterrupted from start to finish: media_started, media_ended
	# Pause button: media_pause
	# Play button: media_started, media_play
	# Stop button: media_stopped, media_ended

	def _on_media_started(self, source):
		#print("************* media started ***************")
		source = obs.calldata_source(source, "source")
		self.on_media_started(ObsSource(source))

	def _on_media_ended(self, source):
		#print("************* media ended ***************")
		source = obs.calldata_source(source, "source")
		self.on_media_ended(ObsSource(source))

	def _on_media_pause(self, source):
		#print("************* media pause ***************")
		source = obs.calldata_source(source, "source")
		self.on_media_pause(ObsSource(source))

	def _on_media_play(self, source):
		#print("************* media play ***************")
		source = obs.calldata_source(source, "source")
		self.on_media_play(ObsSource(source))

	def _on_media_stopped(self, source):
		#print("************* media stopped ***************")
		source = obs.calldata_source(source, "source")
		self.on_media_stopped(ObsSource(source))

	def on_source_create(self, source):
		pass

	def on_source_destroy(self, source):
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

