from flask import flash
from ewmh import EWMH

def find_second_window():
	second_window_name = "Zoom"
	wm = EWMH()
	for window in wm.getClientList():
		name = wm.getWmName(window).decode("utf-8")
		if name == second_window_name:
			return "%d\r\n%s\r\n%s" % (window.id, name, window.get_wm_class()[0])
	flash("Second Zoom window not found.")
	return None

