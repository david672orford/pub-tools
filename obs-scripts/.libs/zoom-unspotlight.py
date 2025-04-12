#! /usr/bin/python3

"""
Control Zoom through the ATSPI (Assistive Technology Service Provider Interface),
the X window manager, and by sending keystroke events.

For this to work Zoom must be started with the following environment variables set:
  QT_ACCESSIBILITY=1
  QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1

FIXME: For now this is a separate script which we run from khplayer-zoom-tracker.py
       using subproccess.run() because we are not sure how to load pyatspi from the
       virtual environment. Plus we are not sure we want to pull GNOME libraries
       into OBS.
"""

import pyatspi

class NoWidget(Exception):
	pass

class NoAction(Exception):
	pass

class ControlZoom:
	def __init__(self):
		self.atspi_desktop = pyatspi.Registry.getDesktop(0)

	# Search an object in the AT-SPI heiarcy to find a particular child.
	# container -- the AT-SPI to be searched
	# role_name -- the role of the child such as "frame", "push button" or "check box"
	# child_names -- list of names for this child
	def find_atspi_child(self, container, role_name, child_names):
		for child in container:
			if child.getRoleName() == role_name:
				if child.name in child_names:
					return child
		raise NoWidget("%s %s not found in %s" % (role_name, child_id, container))

	def do_action(self, widget, action_name):
		"""Perform the named AT-SPI action on widget"""
		actions = widget.queryAction()
		for i in range(actions.nActions):
			if actions.getName(i) == action_name:
				actions.doAction(i)
				return
		raise NoAction("Action %s not found!" % action_name)

	def press_button(self, container, child_names):
		"""Find the indicated AT-SPI child push button and press it"""
		widget = self.find_atspi_child(container, "push button", child_names)
		self.do_action(widget, "Press")

	def unspotlight(self):
		"""Find the Remove spotlight button and press it"""
		zoom = self.find_atspi_child(self.atspi_desktop, "application", "zoom")
		conference_window = self.find_atspi_child(zoom, "frame", ["Meeting", "Конференция"])
		self.press_button(conference_window, ["Remove spotlight", "Удалить отслеживание"])

if __name__ == "__main__":
	control_zoom = ControlZoom()
	control_zoom.unspotlight()
