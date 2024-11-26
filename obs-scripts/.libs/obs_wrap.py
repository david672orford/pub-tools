import obspython as obs
import inspect
from contextlib import contextmanager
import json

class ObsWidget:
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
	def __str__(self):
		return str(self.__dict__)

class ObsScene:
	def __init__(self, scene):
		self.scene = scene

	# Name of scene as seen by user
	@property
	def name(self):
		return obs.obs_source_get_name(self.scene)

class ObsSource:
	def __init__(self, source):
		self.source = obs.calldata_source(source, "source")

	# The source type such as "source_ffmpeg" or "source_vlc"
	@property
	def id(self):
		return obs.obs_source_get_id(self.source)

	# The name of the source as seen by the user
	@property
	def name(self):
		return obs.obs_source_get_name(self.source)

	# An object to which we attach signal handlers to this source
	@property
	def signal_handler(self):
		return obs.obs_source_get_signal_handler(self.source)

	@property
	def settings(self):
		raw_settings = obs.obs_source_get_settings(self.source)
		json_text = obs.obs_data_get_json(raw_settings)
		settings = json.loads(json_text)
		obs.obs_data_release(raw_settings)
		return settings

	# Duration of recording in milliseconds
	@property
	def duration(self):
		return obs.obs_source_media_get_duration(self.source)

	# Playhead position in milliseconds from the start
	@property
	def time(self):
		return obs.obs_source_media_get_time(self.source)

	# Halt playback
	def stop(self):
		obs.obs_source_media_stop(self.source)

	def __str__(self):
		return "<ObsSource id=%s name=%s>" % (self.id, self.name)

# For iterating the scene and source lists
@contextmanager
def freeing(source_list):
	try:
		yield source_list
	finally:
		obs.source_list_release(source_list)

# Derive your OBS script class from this
class ObsScript:
	gui = []

	def __init__(self, debug=False):
		self.debug = debug
		self._install_callbacks(inspect.currentframe().f_back.f_globals)

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
	# 1) script_unload
	#
	#===================================================================

	# Install OBS callback functions in the global namespace of the calling module
	def _install_callbacks(self, g):
		g['script_description'] = lambda: self.__doc__
		g['script_load'] = lambda settings: self._script_load(settings)
		g['script_unload'] = lambda: self._script_unload()
		g['script_save'] = lambda settings: self._script_save(settings)
		g['script_defaults'] = lambda settings: self._script_defaults(settings)
		g['script_properties'] = lambda: self._script_properties()
		g['script_update'] = lambda settings: self._script_update(settings)

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
				setattr(settings, widget.name, obs.obs_data_get_string(raw_settings, widget.name))
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
			print("*** script_defaults()")
		for widget in self.gui:
			if widget.type == "bool":
				obs.obs_data_set_default_bool(raw_settings, widget.name, widget.default_value)
			elif widget.type == "bool":
				obs.obs_data_set_default_int(raw_settings, widget.name, widget.default_value)
			elif widget.type == "float":
				obs.obs_data_set_default_double(raw_settings, widget.name, widget.default_value)
			elif widget.type in ("text", "select"):
				obs.obs_data_set_default_string(raw_settings, widget.name, widget.default_value)
			elif widget.type != "button":
				raise AssertionError("Undefined widget type: %s" % widget.type)

	def _script_load(self, raw_settings):
		if self.debug:
			print("*** script_load()")

		self.on_load(self._pythonize_settings(raw_settings))

		# Watch frontend events until OBS finishes loading. We dare not leave
		# this handler installed since it creates lockups when scripts switch
		# scenes. See: https://stackoverflow.com/questions/73142444/obs-crashes-when-set-current-scene-function-called-within-a-timer-callback-pyth
		def on_event(event):
			if self.debug:
				print("*** event:", event)
			if event == obs.OBS_FRONTEND_EVENT_FINISHED_LOADING:
				if self.debug:
					print("*** finished loading")
				self.enqueue(lambda: self.on_finished_loading())
				obs.obs_frontend_remove_event_callback(on_event)
		obs.obs_frontend_add_event_callback(on_event)

	# Called just before settings screen is displayed to build the GUI
	def _script_properties(self):	# why not settings?
		if self.debug:
			print("*** script_properties()")
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
			print("*** script_update()")
		settings = self._pythonize_settings(raw_settings)
		if self.debug:
			print("*** settings:", settings)
		self.on_gui_change(settings)

	# Called just before script_unload()
	# Documentation is a bit unclear about this, but it sounds like it
	# gives the script an opportunity to stash things in the settings object.
	def _script_save(self, settings):
		if self.debug:
			print("*** script_save()")
		#self.on_save()

	# OBS is about to shut down
	def _script_unload(self):
		if self.debug:
			print("*** script_unload()")
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

	#===================================================================
	# Call these as needed from derived classes
	#===================================================================

	def get_scene(self):
		scene = obs.obs_frontend_get_current_scene()
		name = obs.obs_source_get_name(scene)
		obs.obs_source_release(scene)
		return name

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
			print("*** source_created:", source)
		self._install_source_listeners(source)
		self.on_source_create(source)

	def _on_source_destroy(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** source_destroy:", source)
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
			print("*** scene activated:", scene_name)
		self.on_scene_activate(scene_name)

	def _on_scene_deactivate(self, source):
		source = obs.calldata_source(source, "source")
		scene_name = obs.obs_source_get_name(source)
		if self.debug:
			print("*** scene deactivated:", scene_name)
		self.on_scene_deactivate(scene_name)

	def _on_source_activate(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** source_activate:", source)
		self.on_source_activate(source)

	def _on_source_deactivate(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** source_deactivate:", source)
		self.on_source_deactivate(source)

	def _on_media_started(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** media_started:", source)
		self.on_media_started(source)

	def _on_media_ended(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** media_ended:", source)
		self.on_media_ended(source)

	def _on_media_pause(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** media_pause:", source)
		self.on_media_pause(source)

	def _on_media_play(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** media_play:", source)
		self.on_media_play(source)

	def _on_media_stopped(self, source):
		source = ObsSource(source)
		if self.debug:
			print("*** media_stopped:", source)
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
