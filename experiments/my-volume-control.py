#! /usr/bin/python3

# https://athenajc.gitbooks.io/python-gtk-3-api/content/gtk-group/gtkscale.html
# https://pypi.org/project/pulsectl-asyncio/ 
# https://github.com/jhenstridge/asyncio-glib/issues/1

# pip3 install asyncio_glib pulsectl_asyncio

app_name = "my-volume"
app_icon = "multimedia-volume-control-symbolic"
app_width = 600

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk
import signal
import pulsectl
import threading
from time import sleep

signal.signal(signal.SIGINT, signal.SIG_DFL)

# Borderless window always-on-top at top-rigth
class VolumePanel(Gtk.Window):
	def __init__(self):
		super().__init__()
		self.set_title(app_name)
		self.set_decorated(False)
		self.set_default_size(app_width, 100)
		self.set_keep_above(True)
		first_monitor_geometry = Gdk.Display.get_default().get_monitor(0).get_geometry()
		self.move(first_monitor_geometry.width-app_width, 0)

		self.box = Gtk.VBox()
		self.box.set_margin_start(15)
		self.box.set_margin_end(15)
		super().add(self.box)

		close_hbox = Gtk.HBox()
		close_button = Gtk.Button(label="X")
		close_hbox.pack_end(close_button, fill=False, expand=False, padding=0)
		self.add(close_hbox)
		close_button.connect("clicked", Gtk.main_quit)

	def add(self, box):
		self.box.pack_start(box, expand=False, fill=False, padding=10)

class VolumeControl(Gtk.Frame):
	def __init__(self, pulse, sink, listener):
		super().__init__(label=sink.description)

		# Some themes do not render this
		self.set_shadow_type(Gtk.ShadowType.OUT)

		self.pulse = pulse
		self.sink = sink
		self.listener = listener

		volume = sink.volume.value_flat * 100.0
		self.adjustment = Gtk.Adjustment(value=volume, lower=0, upper=153, step_increment=1, page_increment=10, page_size=0)
		self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adjustment)
		self.scale.set_digits(0)
		self.scale.add_mark(100, Gtk.PositionType.LEFT, None)
		self.add(self.scale)

		# Slider changes volume which changes slider. This prevents looping.
		self.change_lock = False

		def on_slider_change(target):
			if not self.change_lock:
				self.change_lock = True
				volume = target.get_value()
				print("Slider change:", volume)
				self.listener.pause()
				self.pulse.volume_set_all_chans(self.sink, volume / 100.0)
				self.listener.resume()
				self.change_lock = False
		self.adjustment.connect("value-changed", on_slider_change)

		def on_volume_change(info):
			if not self.change_lock:
				self.change_lock = True
				GLib.idle_add(lambda: _on_volume_change(info))
		def _on_volume_change(info):
			print("Volume change:", info.mute, info.volume.value_flat)
			volume = info.volume.value_flat * 100.0
			self.adjustment.set_value(volume)
			self.change_lock = False
		listener.listeners[sink.index] = on_volume_change	

class PulseListener:
	def __init__(self, pulse):
		self.pulse = pulse
		self.listeners = {}
		self.event = None
		self.paused = False
		self.listening = False
		def queue_event(event):
			self.event = event
			raise pulsectl.PulseLoopStop
		pulse.event_mask_set("all")
		pulse.event_callback_set(queue_event)
	def run(self):
		while True:
			self.listening = True
			self.pulse.event_listen(timeout=60)
			self.listening = False
			if self.event is not None:
				node_index = self.event.index
				if node_index in self.listeners:
					try:
						info = self.pulse.sink_info(node_index)
						self.listeners[node_index](info)
					except pulsectl.PulseIndexError:
						print("PulseIndexError!")
				self.event = None
			while self.paused:
				sleep(1.0)
	def pause(self):
		self.paused = True
		while self.listening:
			self.pulse.event_listen_stop()
			sleep(0.01)
	def resume(self):
		self.paused = False

def main():
	panel = VolumePanel()

	pulse = pulsectl.Pulse(app_name, threading_lock=True)
	#pulse.connect()

	listener = PulseListener(pulse)

	for node in pulse.sink_list() + pulse.source_list():
		print(node)
		if not node.name.endswith(".monitor"):
			control = VolumeControl(pulse, node, listener)
			panel.add(control)

	for client in pulse.client_list():
		print("client:", client)

	thread = threading.Thread(target=lambda: listener.run())
	thread.daemon = True
	thread.start()

	panel.show_all()
	Gtk.main()

main()
