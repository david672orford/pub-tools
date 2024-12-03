from flask import current_app

try:
	import obspython as obs
	in_obs = True
except ImportError:
	in_obs = False

def get_theme():

	# config.py has top priority
	theme = current_app.config.get("THEME")

	# Otherwise go with "basic-light" unless running inside OBS in and OBS is in dark mode.
	if theme is None:
		if in_obs and obs.obs_frontend_is_theme_dark():
			theme = "basic-dark"
		else:
			theme = "basic-light"

	return theme
