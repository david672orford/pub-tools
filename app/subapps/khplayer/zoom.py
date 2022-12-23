from flask import flash
import os, types
import subprocess
import pyatspi
from ewmh import EWMH
from Xlib import X, XK, ext
from time import sleep

class AutomateError(Exception):
	pass

class NoSuchWidget(AutomateError):
	pass

class NoSuchAction(AutomateError):
	pass

#=============================================================================
# Automation based on the screen reader API
#=============================================================================

class Container:
	def __init__(self, wm, parent, role_name, child_id, atspi_obj):
		self.wm = wm
		self.parent = parent
		self.role_name = role_name
		self.child_id = child_id
		self.atspi_obj = atspi_obj

	def __str__(self):
		return "<Container %s %s>" % (self.role_name, self.child_id)

	# Search the ATSPI tree below this object for the specified child.
	def find_child(self, role_name, child_id):
		if type(child_id) is int:
			rule = lambda index, child: index == child_id
		elif type(child_id) is str:
			rule = lambda index, child: child.name == child_id
		elif type(child_id) in (tuple, list, set):
			rule = lambda index, child: child.name in child_id
		else:
			raise TypeError()

		index = 0
		for child in self.atspi_obj:
			#print("child:", child)
			if child.getRoleName() == role_name:
				if rule(index, child):
					return Container(self.wm, self, role_name, child_id, child)
				index += 1
		raise NoSuchWidget("%s %s not found in %s" % (role_name, child_id, self.atspi_obj))

	# We use this version when searching for children which appear as a result
	# of the previous action. This gives the program time to produce them.
	def find_child_with_retry(self, role_name, child_id):
		for i in range(20):
			sleep(.5)
			try:
				return self.find_child(role_name, child_id)
			except NoSuchWidget:
				pass
			except Exception as e:
				raise NoSuchWidget("Exception: %s" % e)
		raise NoSuchWidget("%s %s not found in %s" % (role_name, child_id, self.atspi_obj))

	# Find the indicated AT-SPI child push button and press it
	def press_button(self, child_id):
		widget = self.find_child("push button", child_id)
		self.do_action(widget, "Press")
	
	# Perform the named AT-SPI action
	def do_action(self, action_name):
		actions = self.atspi_obj.queryAction()
		for i in range(actions.nActions):
			if actions.getName(i) == action_name:
				actions.doAction(i)
				break
		else:
			raise NoSuchAction("%s not found in %s" % (action_name, self))

	# Ask the window manager to set input focus to the named window
	def focus_window(self, find_name):
		for attempt in range(20):
			for window in self.wm.getClientList():
				name = self.wm.getWmName(window).decode("utf-8")
				if name == find_name:
					self.wm.display.set_input_focus(window.id, X.RevertToParent, X.CurrentTime)
					self.wm.display.flush()
					return
			sleep(.5)
		raise NoSuchWidget("No window with title %s" % find_name)

	def get_description(self):
		return self.atspi_obj.get_description()

	def grab_focus(self):
		if self.role_name == "frame":	# "frame" is ATSPI terminology for a window
			window_id = self.focus_window(self.get_description())
		else:
			comp = self.atspi_obj.queryComponent()
			comp.grabFocus()

	def get_text(self):
		return self.atspi_obj.queryText().getText(0, -1)

	def enter_text(self, text, verify=False):

		# FIXME: This messes with the list of available layouts, doesn't it?
		# Switch keyboard map to English
		os.system("setxkbmap -layout en,ru -option grp:caps_toggle")

		# Send control-A to select the existing text
		pyatspi.Registry.generateKeyboardEvent(37, None, pyatspi.KEY_PRESS)
		pyatspi.Registry.generateKeyboardEvent(38, None, pyatspi.KEY_PRESS)
		pyatspi.Registry.generateKeyboardEvent(38, None, pyatspi.KEY_RELEASE)
		pyatspi.Registry.generateKeyboardEvent(37, None, pyatspi.KEY_RELEASE)

		# Send the text 
		pyatspi.Registry.generateKeyboardEvent(0, text, pyatspi.KEY_STRING)

		# Wait for the text to appear
		if verify:
			for i in range(3):
				sleep(.5)
				if self.get_text() == text:
					break
			else:
				raise AutomateError("Text not set")
		else:
			sleep(1)

	def send_tab(self):
		pyatspi.Registry.generateKeyboardEvent(23, None, pyatspi.KEY_PRESS)
		pyatspi.Registry.generateKeyboardEvent(23, None, pyatspi.KEY_RELEASE)

class Automate(Container):
	def __init__(self):
		self.wm = EWMH()
		self.parent = None
		self.role_name = "desktop"
		self.child_id = 0
		self.atspi_obj = pyatspi.Registry.getDesktop(0)

	def find_application(self, app_name):
		return self.find_child_with_retry("application", app_name)

#=============================================================================
# Control of Zoom based on the Screenreader API
#=============================================================================

class ZoomControl:
	def __init__(self, config, progress_callback):
		self.config = config
		self.progress_callback = progress_callback

	def start_meeting(self):	
		automate = Automate()
		zoom = automate.find_application("zoom")
		
		frame = zoom.find_child("frame", 0)
		assert frame.get_description() in ["Zoom Cloud Meetings", "Облачные конференции Zoom"]
		frame.grab_focus()

		self.progress_callback("Logging in...")
		
		# First page: Two options: Join a conference or log in
		frame.find_child("push button", 1).do_action("Press")
		
		# Second page: Log in screen
		username = frame.find_child("text", 0)
		username.grab_focus()
		username.enter_text(self.config["username"])
		
		username.send_tab()
		password = frame.find_child("text", 1)
		password.enter_text(self.config["password"], verify=False)
		
		signin_button = frame.find_child("push button", 4)	# TODO: maybe use name
		signin_button.do_action("Press")

		self.progress_callback("Joining or starting meeting...")

		# Third page: New Meeting, Join, etc.
		frame = zoom.find_child_with_retry("frame", ["Zoom - Licensed Account", "Zoom - Лицензионная учетная запись"])
		frame.find_child("filler", ["Home","Главная"]).find_child("push button", ["Join","Войти"]).do_action("Press")
		
		# Forth page: Choose a Meeting Dialog
		frame = zoom.find_child_with_retry("frame", 2)
		assert frame.get_description() == "Zoom"
		frame.grab_focus()
		
		meeting_id = frame.find_child("text", 0)
		meeting_id.grab_focus()
		meeting_id.enter_text(self.config["meetingid"])
		
		if "participant-name" in self.config:
			participant = frame.find_child("text", 1)
			participant.grab_focus()
			participant.enter_text(self.config["participant-name"])
		
		start_button = frame.find_child("push button", 1)
		start_button.do_action("Press")

		self.progress_callback("In meeting.")

#=============================================================================
# Alternative control of Zoom based only in keystroke injection
#=============================================================================

class AltZoomControl:
	def __init__(self, config):
		self.config = config
		self.wm = EWMH()
		self.display = self.wm.display

	# Find a window in the list of the window manager's clients.
	def find_wm_window(self, find_name):
		print("find_wm_window:", find_name)
		for attempt in range(20):
			for window in self.wm.getClientList():
				name = self.wm.getWmName(window)
				if name is not None:
					name = name.decode("utf-8")
				#print("Window name: '%s'" % name)
				if name == find_name:
					return window
			sleep(.25)
		raise NoSuchWidget(find_name)

	def focus_window(self, window):
		self.display.set_input_focus(window, X.RevertToParent, X.CurrentTime)

	def get_window(self, window_name):
		window = self.find_wm_window(window_name)
		self.focus_window(window)

	# Send keys to a window using the XTEST extension
	def send_keys(self, keynames):
		print("send_keys:", keynames)
		for keyname in keynames:
			keycode_stack = []	
			for keyname_part in keyname.split("-"):
				keysym = XK.string_to_keysym(keyname_part)
				assert keysym != 0, "No keysym for %s" % keyname_part
				keycode = self.display.keysym_to_keycode(keysym)
				#print("KeyPress:", keycode)
				ext.xtest.fake_input(self.display, X.KeyPress, keycode)
				keycode_stack.insert(0, keycode)
			for keycode in keycode_stack:
				#print("KeyRelease:", keycode)
				ext.xtest.fake_input(self.display, X.KeyRelease, keycode)
			self.display.flush()

	# See:
	# https://chromium.googlesource.com/chromiumos/platform/autox/+/8b510c7d95f89c46d8349f9e13eaf5fd422795a0/autox.py
	keysyms = {
		" ": "space",
		"@": "Shift_L-2",
		".": "period",
		"/": "slash",
		"$": "Shift_L-dollar",
		}
	def send_text(self, text):
		keynames = []
		for char in text:
			if char in self.keysyms:
				keynames.append(self.keysyms[char])
			elif char.isupper():
				keynames.append("Shift_L-" + char)
			else:
				keynames.append(char)
		self.send_keys(keynames)

	def start_meeting(self):
		self.get_window("Zoom Cloud Meetings")

		# Tab to "Sign In" button, give it a second to settle, and press Return
		self.send_keys(["Tab", "Tab"])
		sleep(1)
		self.send_keys(["Return"])
		sleep(1)

		# Enter username and password
		self.get_window("Zoom Cloud Meetings")
		self.send_keys(["Tab", "Tab", "Tab"])
		self.send_text(self.config["username"])
		self.send_keys(["Tab"])
		self.send_text(self.config["password"])
		sleep(2)
		self.send_keys(["Tab", "Tab", "Return"])

		# Tab to Join Meeting and 'press' it
		self.get_window("Zoom - Licensed Account")
		self.send_keys([
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",
			"Tab",		# Required under kh account
			"Return",
			])

		# Wait for the join meeting dialog, enter meeeting ID
		self.get_window("Zoom")
		sleep(2)
		self.send_keys(["Tab", "Tab"])
		self.send_text(self.config["meetingid"])
		sleep(2)
		self.send_keys([
			"Tab",
			"Tab",
			])
		if "participant-name" in self.config:
			sleep(2)
			self.send_keys([
				"Control_L-a",		# select all
				"BackSpace",
				])	
			self.send_text(self.config["participant-name"])
		self.send_keys([
			"Tab",
			"Tab",
			"Tab",
			"Return",
			])

		# If we exit too soon, it doesn't work.
		sleep(10)

#=============================================================================
# Public functions
#=============================================================================

def start_meeting(config, logfile, progress_callback):

	# If Zoom is already running, shut it down.
	i = 0
	while os.system("killall zoom") == 0:
		progress_callback("Shutting down old Zoom: %d" % i)
		os.wait3(os.WNOHANG)
		sleep(1)
		i += 1

	# Start Zoom with screen-reader integration enabled
	os.environ["QT_ACCESSIBILITY"] = "1"
	os.environ["QT_LINUX_ACCESSIBILITY_ALWAYS_ON"] = "1"

	progress_callback("Starting Zoom...")
	with open(logfile, "w") as fh:
		zoom_proc = subprocess.Popen(["zoom"], stderr=subprocess.STDOUT, stdout=fh)

	zoom = ZoomControl(config, progress_callback)
	zoom.start_meeting()

	return zoom_proc

def find_second_window():
	second_window_name = "Zoom"
	wm = EWMH()
	for window in wm.getClientList():
		name = wm.getWmName(window).decode("utf-8")
		if name == second_window_name:
			return "%d\r\n%s\r\n%s" % (window.id, name, window.get_wm_class()[0])
	flash("Second Zoom window not found.")
	return None


