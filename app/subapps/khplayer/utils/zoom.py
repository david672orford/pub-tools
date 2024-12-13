try:
	from ewmh import EWMH
	have_ewmh = True
except ModuleNotFoundError:
	have_ewmh = False

from ....utils.background import async_flash
from ....utils.babel import gettext as _
from .controllers import obs

def zoom_tracker_loaded():
	"""Is the KH Player Zoom Tracker running in OBS?"""
	for input in obs.get_input_list():
		if input["inputKind"] == "khplayer-zoom-participant":
			return True
	return False

def find_second_window():
	"""Look for the Zoom second-monitor window and return its address for OBS window capture"""
	second_window_name = "Zoom Workplace"
	if have_ewmh:
		wm = EWMH()
		for window in wm.getClientList():
			name = wm.getWmName(window).decode("utf-8")
			if name == second_window_name:
				return "%d\r\n%s\r\n%s" % (window.id, name, window.get_wm_class()[0])
		async_flash(_("Second Zoom window not found."))
		return None
	async_flash("Not implemented")
	return None
