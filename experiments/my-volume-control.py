#! /usr/bin/python3
#
# Custom volume control for PulseAudio
#
# ## Currently Used
# * [Python Gtk+ 3.0 API](https://athenajc.gitbooks.io/python-gtk-3-api/content/)
# * [Python bindings for Libpulse](https://github.com/mk-fg/python-pulse-control/)
#
# ## For the Future
# * [Python bindings for Libpulse with Async](https://pypi.org/project/pulsectl-asyncio/ 
# * [GLib event loop integration for asyncio](https://github.com/jhenstridge/asyncio-glib)
# * [Attempts to integrate above with Gtk](https://github.com/jhenstridge/asyncio-glib/issues/1)
#

app_name = "my-volume"
app_icon = "multimedia-volume-control-symbolic"
app_width = 600

import threading
from time import sleep

# Load the Gtk GUI toolkit
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk

# Interface to PulseAudio
# pip3 install pulsectl
import pulsectl

# Borderless window always-on-top at top-right
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

		top_hbox = Gtk.HBox()
		title = Gtk.Label(label="Volume Controls")
		top_hbox.pack_start(title, fill=False, expand=False, padding=0)
		close_button = Gtk.Button(label="X")
		close_button.connect("clicked", Gtk.main_quit)
		top_hbox.pack_end(close_button, fill=False, expand=False, padding=0)
		self.add(top_hbox)

	def add(self, box):
		self.box.pack_start(box, expand=False, fill=False, padding=10)

class VolumeControl(Gtk.Frame):
	def __init__(self, pulse_wrapper, audio_device):
		self.pulse_wrapper = pulse_wrapper
		self.audio_device = audio_device
		super().__init__(label=audio_device.description)

		# Some themes do not render this
		self.set_shadow_type(Gtk.ShadowType.OUT)

		volume = audio_device.volume.value_flat * 100.0
		self.adjustment = Gtk.Adjustment(value=volume, lower=0, upper=153, step_increment=1, page_increment=10, page_size=0)
		self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adjustment)
		self.scale.set_digits(0)
		self.scale.add_mark(100, Gtk.PositionType.LEFT, None)

		self.mute = Gtk.CheckButton(label="Mute")
		self.mute.set_active(audio_device.mute)

		box = Gtk.HBox()
		box.pack_start(self.scale, expand=True, fill=True, padding=0)
		box.pack_start(self.mute, expand=False, fill=False, padding=0)
		self.add(box)

		self.expect_slider = 0
		self.expect_mute = 0
		self.expect_pulseaudio = 0

		def on_slider_change(target):
			#print("Slider change:", target.get_value())
			if self.expect_slider > 0:
				self.expect_slider -= 1
			else:
				self.expect_pulseaudio += 1
				volume = target.get_value()
				self.pulse_wrapper.volume_set_all_chans(self.audio_device, volume / 100.0)
		self.adjustment.connect("value-changed", on_slider_change)

		def on_mute_checkbox_changed(target):
			#print("Mute toggled", self.mute.get_active())
			if self.expect_mute > 0:
				self.expect_mute -= 1
			else:
				self.expect_pulseaudio += 1
				self.pulse_wrapper.set_mute(self.audio_device, self.mute.get_active())
		self.mute.connect("toggled", on_mute_checkbox_changed)

		# PulseAudio reports the state of the source or audio_device has changed
		def on_volume_change(info):
			#print("PulseAudio change:", info, info.mute, info.volume.value_flat)
			if self.expect_pulseaudio > 0:
				self.expect_pulseaudio -= 1
			else:
				self.expect_slider += 1
				GLib.idle_add(lambda: _on_volume_change(info))
		def _on_volume_change(info):
			#print("_PulseAudio change:", info.mute, info.volume.value_flat)
			volume = info.volume.value_flat * 100.0
			self.adjustment.set_value(volume)
			if info.mute != self.mute.get_active():
				self.expect_mute += 1
				self.mute.set_active(info.mute)
		pulse_wrapper.subscribe(audio_device, on_volume_change)

class PulseWrapper:
	def __init__(self, pulse):
		self.pulse = pulse
		self._subscribers = {}
		self._event = None				# event currently being processed
		self._listener_paused = False
		self._in_listener = False

		def queue_event(event):
			self._event = event
			raise pulsectl.PulseLoopStop
		pulse.event_mask_set("source", "sink")
		pulse.event_callback_set(queue_event)

	def subscribe(self, audio_device, callback):
		self._subscribers[audio_device.index] = callback

	def run_event_listener(self):
		while True:
			self._in_listener = True
			self.pulse.event_listen(timeout=60)
			self._in_listener = False
			if self._event is not None:
				print("event:", self._event, self._event.facility)
				node_index = self._event.index
				if node_index in self._subscribers:
					try:
						if self._event.facility == pulsectl.PulseEventFacilityEnum.source:
							info = self.pulse.source_info(node_index)
						else:
							info = self.pulse.sink_info(node_index)
						self._subscribers[node_index](info)
					except pulsectl.PulseIndexError:
						print("PulseIndexError!")
				self._event = None
			while self._listener_paused:
				sleep(1.0)

	def _pause_listener(self):
		self._listener_paused = True
		while self._in_listener:
			self.pulse.event_listen_stop()
			sleep(0.01)

	def _resume_listener(self):
		self._listener_paused = False

	def volume_set_all_chans(self, audio_device, volume):
		self._pause_listener()
		self.pulse.volume_set_all_chans(audio_device, volume)
		self._resume_listener()

	def set_mute(self, audio_device, mute:bool):
		print("set_mute:", mute)
		self._pause_listener()
		if type(audio_device) is pulsectl.PulseSourceInfo:
			self.pulse.source_mute(audio_device.index, mute)
		else:
			self.pulse.sink_mute(audio_device.index, mute)
		self._resume_listener()

def main():
	panel = VolumePanel()

	pulse = pulsectl.Pulse(app_name, threading_lock=True)
	pulse_wrapper = PulseWrapper(pulse)

	for audio_device in pulse.sink_list() + pulse.source_list():
		print(type(audio_device), audio_device)
		if not audio_device.name.endswith(".monitor"):
			control = VolumeControl(pulse_wrapper, audio_device)
			panel.add(control)

	for client in pulse.client_list():
		print("client:", client)

	thread = threading.Thread(target=lambda: pulse_wrapper.run_event_listener())
	thread.daemon = True
	thread.start()

	panel.show_all()
	Gtk.main()

main()
