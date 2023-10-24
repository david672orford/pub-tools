try:
	from ewmh import EWMH
	have_ewmh = True
except ModuleNotFoundError:
	have_ewmh = False

from flask import flash
from ....utils.babel import gettext as _

def find_second_window():
	second_window_name = "Zoom"
	if have_ewmh:
		wm = EWMH()
		for window in wm.getClientList():
			name = wm.getWmName(window).decode("utf-8")
			if name == second_window_name:
				return "%d\r\n%s\r\n%s" % (window.id, name, window.get_wm_class()[0])
		flash(_("Second Zoom window not found."))
		return None
	flash("Not implemented")
	return None

