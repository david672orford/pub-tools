# OBS Studio Plugin which automatically starts the virtual camera and
# fullscreen projector when the program starts

import obspython as obs

class MyObsScript:
	description = "Autostart virtual camera and fullscreen projector"

	def __init__(self):
		g = globals()
		g['script_defaults'] = lambda settings: self.script_defaults(settings)
		g['script_description'] = lambda: self.description
		g['script_update'] = lambda settings: self.script_update(settings)
		g['script_properties'] = lambda: self.script_properties()
		g['script_unload'] = lambda: self.script_unload()

	# Settings screen defaults
	def script_defaults(self, settings):
		obs.obs_data_set_default_string(settings, "screen", "2")

	# Settings screen widgets
	def script_properties(self):
		props = obs.obs_properties_create()
		screens = obs.obs_properties_add_list(props, "screen", "Screen", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
		obs.obs_property_list_add_string(screens, "Screen 1", "0")
		obs.obs_property_list_add_string(screens, "Screen 2", "1")
		obs.obs_property_list_add_string(screens, "Screen 3", "2")
		return props

	# Accept settings (possibly changed)
	def script_update(self, settings):
		screen = int(obs.obs_data_get_string(settings, "screen"))
		print("screen:", screen)
		obs.obs_frontend_start_virtualcam()
		obs.obs_frontend_open_projector("Program", screen, "", "Video Output")

	# Shutdown
	def script_unload(self):
		obs.obs_frontend_stop_virtualcam()

MyObsScript()

