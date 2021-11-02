#
# Control Zoom through the Window manager interface the XTEST extension
# sudo apt install python3-ewmh
#

from ewmh import EWMH
from Xlib import X, protocol, XK, ext
from time import sleep
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class NoWidget(Exception):
	pass

class ZoomControl:
	conference_window_title = "Конференция Zoom"
	sharing_dialog_title = "Выберите окно или приложение, которое вы хотите совместно использовать"
	camera_view_title = "Dummy video device (0x0000)"

	def __init__(self):
		self.wm = EWMH()
		self.display = self.wm.display

		self.dialog_window = None
		self.dialog_window_hidden = False
		self.camera_view_window = None

	def is_sharing(self):
		return self.camera_view_window is not None

	# Find a window in the list of the window manager's clients.
	def find_wm_window(self, find_name):
		logger.debug("find_wm_window: %s", find_name)
		for attempt in range(20):
			for window in self.wm.getClientList():
				name = self.wm.getWmName(window)
				if name is not None:
					name = name.decode("utf-8")
				#print("Window name: '%s'" % name)
				if name == find_name:
					return window
			sleep(.25)
		raise NoWidget("No window with title \"%s\"" % find_name)
	
	# Send keys to a window using the XTEST extension
	def send_keys(self, window, keynames):
		logger.debug("send_keys: %s", keynames)
		self.display.set_input_focus(window, X.RevertToParent, X.CurrentTime)
		for keyname in keynames:
			keycode_stack = []	
			for keyname_part in keyname.split("-"):
				keysym = XK.string_to_keysym(keyname_part)
				assert keysym != 0, "No keysym for %s" % keyname_part
				keycode = self.display.keysym_to_keycode(keysym)
				ext.xtest.fake_input(self.display, X.KeyPress, keycode)
				keycode_stack.insert(0, keycode)
			for keycode in keycode_stack:
				ext.xtest.fake_input(self.display, X.KeyRelease, keycode)
		self.display.flush()

	# Simulate a click with the left mouse button
	def mouse_click(self, window, xCoord, yCoord):
		logger.debug("mouse_click()")
		self.display.set_input_focus(window, X.RevertToParent, X.CurrentTime)
		focus = self.display.get_input_focus().focus
		focus.warp_pointer(xCoord, yCoord)
		button = 1
		ext.xtest.fake_input(focus, X.ButtonPress, button, x=xCoord, y=yCoord)
		ext.xtest.fake_input(focus, X.ButtonRelease, button, x=xCoord, y=yCoord)	

	# Open the sharing dialog, set options, and select the 2nd camera
	# source, but do not start sharing.
	def open_sharing_dialog(self, hide=False):
		logger.debug("open_sharing_dialog()")

		zoom_window = self.find_wm_window(self.conference_window_title)

		# Open sharing dialog
		self.send_keys(zoom_window, ["Alt_L-S"])

		# Find the screen sharing dialog 
		self.dialog_window = self.find_wm_window(self.sharing_dialog_title)

		# Do a screenshot of the "Share Audio" checkbox. If it has no blue, click on it.
		geometry = self.dialog_window.get_geometry()
		#print(geometry.width, geometry.height)
		while True:
			image = self.dialog_window.get_image(10, geometry.height - 30, 20, 20, X.ZPixmap, 0xffffffff)
			image_hex = image.data.hex('-',-4)
			logger.debug(image_hex)
			if image_hex.startswith("ffffffff-ffffffff-ffffffff-"):						# white background of dialog box
				break
			sleep(0.2)
		#from PIL import Image
		#Image.frombytes("RGB", (20, 20), image.data, "raw", "BGRX").show()
		if not "-ed720eff-" in image_hex:		# if no blue pixels,
			self.mouse_click(self.dialog_window, 10 + 10, geometry.height - 30 + 10)	# middle of image area

		# Select the second camera as input
		keys = [
			"Tab",		# Focus on "Share Sound" checkbox
			"Tab",		# Focus on "Optimize for Video" checkbox
			"Tab",		# Focus on "Start Sharing" button
			"Tab",		# Focus on tab buttons at top
			"Right",	# Focus on the "More" tab button
			"Tab",		# move into body of tab
			"Right",	# From "Share part of screen" to "Share computer sound"
			"Right",	# From "Share computer sound" to "2nd camera"
			]

		self.send_keys(self.dialog_window, keys)

		# Optionally hide the dialog window by unmapping it
		if hide:
			self.dialog_window.unmap()
			self.wm.display.flush()
		self.dialog_window_hidden = hide

	# If the sharing dialog is not yet open, open it. Press the
	# button to start sharing.
	def start_screensharing(self):
		logger.info("start_screensharing()")

		if self.dialog_window is None:
			self.open_sharing_dialog()

		if self.dialog_window_hidden:
			self.dialog_window.map()
			self.wm.display.flush()
			self.dialog_window = self.find_wm_window(self.sharing_dialog_title)

		# Click the star Start Sharing button. This closes the dialog.
		self.mouse_click(self.dialog_window, 675, 420)
		self.dialog_window = None

		# Wait for the video output window to appear. Turn off fullscreen mode, make it small,
		# move it to the lower left corner of the desktop.
		sleep(.1)
		self.camera_view_window = self.find_wm_window(self.camera_view_title)
		self.wm.setWmState(self.camera_view_window, 0, '_NET_WM_STATE_FULLSCREEN')
		self.wm.setMoveResizeWindow(
			self.camera_view_window,
			X.SouthEastGravity,
			self.display.screen().width_in_pixels, self.display.screen().height_in_pixels,
			320, 240
			)
		self.wm.display.flush()

	def stop_screensharing(self):
		logger.info("stop_screensharing()")
		if self.camera_view_window is not None:
			self.wm.setCloseWindow(self.camera_view_window)
			self.wm.display.flush()
			self.camera_view_window = None
		if self.dialog_window is not None:
			self.wm.setCloseWindow(self.dialog_window)
			self.wm.display.flush()
			self.dialog_window = None

# Test
if __name__ == "__main__":
	import sys
	if sys.argv[1] == "test":
		zoom = ZoomControl()
		zoom.open_sharing_dialog(hide=False)
		sleep(3)
		zoom.start_screensharing()
		sleep(10)
		zoom.stop_screensharing()
	elif sys.argv[1] == "list-wm-clients":
		wm = EWMH()
		client_list = wm.getClientList()
		for window in client_list:
			name = wm.getWmName(window).decode("utf-8")
			print(window.id, name)

