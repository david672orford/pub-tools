#
# Control Zoom through the ATSPI (Assistive Technology Service Provider Interface),
# the X window manager, and by sending keystroke events.
#
# For this to work Zoom must be started with the following environment variables set:
#  QT_ACCESSIBILITY=1
#  QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
#
# We are not using this method since XTEST is faster and does not require Zoom
# to be started in any particular way. But, we are keeping this code around for
# future reference.
#

import pyatspi
from ewmh import EWMH
from Xlib import X, protocol, XK, ext
from time import sleep

class NoWidget(Exception):
	pass

class ZoomControl:
	def __init__(self):
		self.wm = EWMH()
		self.display = self.wm.display
		self.atspi_desktop = pyatspi.Registry.getDesktop(0)

		self.dialog_atspi = None
		self.dialog_id = None
		self.camera_view = None

	#	pyatspi.Registry.registerEventListener(self.on_window, 'window')
	#	pyatspi.Registry.registerEventListener(self.on_window, 'window:destroy')
	#
	#def on_window(self, event):
	#	print("window event:", event)

	# Find a window in the list of the window manager's clients.
	def find_wm_window(self, find_name):
		for attempt in range(20):
			for window in self.wm.getClientList():
				name = self.wm.getWmName(window).decode("utf-8")
				#print("Window name: '%s'" % name)
				if name == find_name:
					return window.id
			sleep(.25)
		raise NoWidget("Failed to find window with title %s" % find_name)
	
	# Send keys to a window using the XTEST extension
	def send_keys_xtest(self, winid, keynames):
		for keyname in keynames:
			keysym = XK.string_to_keysym(keyname)
			keycode = self.display.keysym_to_keycode(keysym)
	
			self.display.set_input_focus(winid, X.RevertToParent, X.CurrentTime)
			ext.xtest.fake_input(self.display, X.KeyPress, keycode)
			ext.xtest.fake_input(self.display, X.KeyRelease, keycode)
		#self.display.sync()
		self.display.flush()
	
	# Search an object in the AT-SPI heiarcy to find a particular child.
	# container -- the AT-SPI to be searched
	# role_name -- the role of the child such as "frame", "push button" or "check box"
	# child_id -- the index of the child among children of that type or its name
	def find_atspi_child(self, container, role_name, child_id):
		counter = 0
		for child in container:
			if child.getRoleName() == role_name:
				if (type(child_id) is int and child_id == counter) or child_id == child.name:
					return child
				counter += 1
		raise NoWidget("%s %s not found in %s" % (role_name, child_id, container))
	
	# Perform the named AT-SPI action
	def do_action(self, widget, action_name):
		actions = widget.queryAction()
		for i in range(actions.nActions):
			if actions.getName(i) == action_name:
				actions.doAction(i)
				return True
		print("Action %s not found!" % action_name)
		return False
	
	# Find the indicated AT-SPI child push button and press it
	def press_button(self, container, child_id):
		widget = self.find_atspi_child(container, "push button", child_id)
		self.do_action(widget, "Press")
	
	# Find the indicated AT-SPI check box and set it to the desired state
	def set_check_box(self, container, child_id, desired_state=True):
		widget = self.find_atspi_child(container, "check box", child_id)
		state = pyatspi.STATE_CHECKED in widget.getState().getStates()
		if state is not desired_state:
			self.do_action(widget, "Toggle")	

	# Open the sharing dialog, set options, and select the 2nd camera
	# source, but do not start sharing.
	def open_sharing_dialog(self, hide=False):
		print("open_sharing_dialog()")

		try:
			zoom = self.find_atspi_child(self.atspi_desktop, "application", "zoom")
			conference_window = self.find_atspi_child(zoom, "frame", "Конференция Zoom")
		except NoWidget as e:
			print("Exception: %s" % e)
			return False

		# Press the button to open the screen sharing dialog
		self.press_button(conference_window, "Демонстрация экрана")

		# Find the screen sharing dialog 
		title = "Выберите окно или приложение, которое вы хотите совместно использовать"
		self.dialog_id = self.find_wm_window(title)
		self.dialog_atspi = self.find_atspi_child(zoom, "frame", title)

		# Make sure the two check boxes at the bottom are checked.
		self.set_check_box(self.dialog_atspi, 0) # "Совместный доступ к звуку")
		self.set_check_box(self.dialog_atspi, 1) # "Оптимизировать для видеоклипа")

		# Select the second camera as input
		self.send_keys_xtest(self.dialog_id, [
			"Tab",		# Share Sound
			"Tab",		# optimize for video
			"Tab",		# Start Sharing
			"Tab",		# tab buttons
			"Right",	# More
			"Tab",		# move into body of tab
			"Right",	# Share computer sound
			"Right"		# 2nd camera
			])

		# Optionally move the sharing dialog window to the background and to the bottom right.
		if hide:
			print("hiding")
			self.wm.setWmState(self.dialog_id, 1, '_NET_WM_STATE_BELOW')
			self.wm.setMoveResizeWindow(
				self.dialog_id,
				X.SouthEastGravity,
				self.display.screen().width_in_pixels, self.display.screen().height_in_pixels,
				0, 0,
				)
			self.wm.display.flush()

		return True

	def close_sharing_dialog(self):
		print("close_sharing_dialog()")
		if self.dialog_atspi is not None:
			self.wm.setCloseWindow(self.dialog_id)
			self.wm.display.flush()
			self.dialog_atspi = None
			self.dialog_id = None

	# If the sharing dialog is not yet open, open it. Press the
	# button to start sharing.
	def start_screensharing(self):
		print("start_screensharing()")

		if self.dialog_atspi is None:
			if not self.open_sharing_dialog():
				return

		# Start sharing
		self.press_button(self.dialog_atspi, "Поделиться")
		self.dialog_atspi = None
		self.dialog_id = None

		# Wait for the video output window to appear. Turn off fullscreen mode, make it small.
		sleep(.1)
		self.camera_view = self.find_wm_window("Dummy video device (0x0000)")
		self.wm.setWmState(self.camera_view, 0, '_NET_WM_STATE_FULLSCREEN')
		self.wm.setMoveResizeWindow(
			self.camera_view,
			X.SouthEastGravity,
			self.display.screen().width_in_pixels, self.display.screen().height_in_pixels,
			320, 240
			)
		self.wm.display.flush()

	def stop_screensharing(self):
		print("stop_screensharing()")
		if self.camera_view is not None:
			self.wm.setCloseWindow(self.camera_view)
			self.wm.display.flush()
			self.camera_view = None

def test():
	zoom = ControlZoom()
	zoom.open_sharing_dialog()
	sleep(10)
	zoom.start_screensharing()
	sleep(10)
	zoom.stop_screensharing()

def list_atspi_heirarcy():
	desktop = pyatspi.Registry.getDesktop(0)
	for application in desktop:
		print(application.name, type(application), application.getRoleName())
		if application.name == 'zoom':
			dump_atspi(application)

def dump_atspi(container, level=0):
	for item in container:
		print(" " * level, item, item.getState().getStates())
		dump_atspi(item, level+2)

if __name__ == "__main__":
	import sys
	if sys.argv[1] == "test":
		test()
	if sys.argv[1] == "list-atspi-heirarcy":
		list_atspi_heirarcy()


