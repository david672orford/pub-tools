# Create a virtual audio cable using Pipewire
# This cable connects the output of OBS to the microphone input of Zoom.
# We also connect the microphone and speakers to this cable.
# Layout looks like this:
#                           Microphone[capture] ---v
# OBS[output] ---> [playback]To-Zoom[monitor] ---> [input]From-OBS[capture] ---> [input]Zoom
#                                   |---> [playback]Speakers

import sys, os, types, re
from subprocess import run, PIPE
from time import sleep
import logging

logger = logging.getLogger(__name__)

def create_cable(patchbay):
	"""Create the virtual cable nodes and connect them together"""
	for name, media_class in (
			("From-OBS", "Audio/Source/Virtual"),
			("To-Zoom", "Audio/Sink"),
		):
		node = patchbay.find_node(name=name)
		if node is None:
			logger.info("Creating %s", name)
			run(["pactl",
				"load-module", "module-null-sink",
				"media.class=" + media_class,
				"sink_name=" + name,
				"sink_properties=device.description=" + name,
				"channel_map=mono",
				], stdout=PIPE, check=True)
		else:
			logger.info("%s already exists", name)

	# Give them a chance to settle
	sleep(.1)

	# Connect them
	patchbay.load()
	patchbay.create_link("To-Zoom:monitor_MONO", "From-OBS:input_MONO")

	return []

def destroy_cable(patchbay):
	"""Delete the virtual cable nodes"""
	for name in ("To-Zoom", "From-OBS"):
		logger.info("Destroying %s", name)
		node = patchbay.find_node(name=name)
		if node is None:
			logger.info("Node \"%s\" does not exist", name)
		else:
			logger.info("Destroying node %d (%s)", node.id, name)
			# FIXME: Deleting From-OBS observed to delete To-Zoom as well! Why?
			run(["pw-cli", "destroy", str(node.id)], check=True)

def connect_peripherals(patchbay, config):
	"""Connect Microphone and Speakers to virtual audio cable"""
	failures = []

	from_obs = patchbay.find_node(name="From-OBS")
	to_zoom = patchbay.find_node(name="To-Zoom")
	if from_obs is None or to_zoom is None:
		failures.append("Virtual audio cable not found")
		return failures

	# Connect the microphone specified in config to input of From-OBS and
	# disconnect any other audio sources.
	if "microphone" not in config:
		failures.append("No microphone selected in configuration")
	else:
		# connect microphone to this
		from_obs_input = from_obs.inputs[0]
		# what should be connected
		microphone = patchbay.find_node(name=config["microphone"])
		if microphone is None:
			failures.append("Selected microphone is not connected")
		else:
			microphone_outputs = microphone.outputs[:]
			# what is already connected
			for link in from_obs_input.links[:]:
				if link.output_port.node.media_class == "Audio/Source":		# a microphone or line in
					try:
						microphone_outputs.remove(link.output_port)
					except ValueError:
						patchbay.destroy_link(link=link)
			# what we didn't find already connected
			for port in microphone_outputs:
				patchbay.create_link(port, from_obs_input)

	# Connect the set of speakers specified in config to the output of To-Zoom
	# and disconnect any other audio sinks.
	if "speakers" not in config:
		failures.append("No speakers selected in configuration")
	else:
		to_zoom_output = to_zoom.outputs[0]
		speakers = patchbay.find_node(name=config["speakers"])
		if speakers is None:
			failures.append("Selected speakers are not connected")
		else:
			speaker_inputs = speakers.inputs[:]
			for link in to_zoom_output.links[:]:
				if link.input_port.node.media_class == "Audio/Sink":		# a speaker or headphones
					try:
						speaker_inputs.remove(link.input_port)
					except ValueError:
						patchbay.destroy_link(link=link)
			for port in speaker_inputs:
				patchbay.create_link(to_zoom_output, port)

	return failures

def connect_obs(patchbay):
	"""Connect OBS audio monitor streams to virtual cable"""
	failures = []

	virtual_cable_node = patchbay.find_node(name="To-Zoom")
	virtual_cable_input = virtual_cable_node.inputs[0]

	# Ensure OBS monitor outputs are connected to the virtual cable and nothing else.
	for node in patchbay.nodes:
		if node.name == "OBS-Monitor":
			for output in node.outputs:
				linked = False
				for link in output.links:
					if link.input_port is virtual_cable_input:
						logger.info("OBS-Monitor already linked to To-Zoom")
						linked = True
					else:
						logger.info("Unlinking OBS-Monitor from %s", link.input_port.node.name)
						patchbay.destroy_link(link=link)
				if not linked:
					logger.info("Linking OBS-Monitor to To-Zoom")
					patchbay.create_link(output, virtual_cable_input)

	return failures

def connect_zoom(patchbay, config):
	"""Connect Zoom input to virtual cable, output to speakers"""
	failures = []

	zoom_input_node = patchbay.find_node(name="ZOOM VoiceEngine", media_class="Stream/Input/Audio")
	if zoom_input_node is None:
		# Switched from warning to info because it just means we started OBS before Zoom.
		# If we were to leave it as a warning, OBS would open the script log window.
		#logger.warning("Zoom input node not found")
		logger.info("Zoom input node not found")
	else:
		# Find the output port on the output end of the virtual audio cable between OBS and Zoom.
		from_obs_output = patchbay.find_node(name="From-OBS").outputs[0]

		# Loop through however many input ports Zoom has. Normally this will be
		# only MONO, but there is a stereo mode.
		for zoom_input in zoom_input_node.inputs:
			linked = False
			for link in zoom_input.links[:]:
				if link.output_port == from_obs_output:
					linked= True
				else:
					patchbay.destroy_link(link=link)
			if not linked:
				patchbay.create_link(from_obs_output, zoom_input)

	if "speakers" in config:
		speakers = patchbay.find_node(name=config["speakers"])
		if speakers is None:
			logger.warning("Speakers not found: %s", config["speakers"])
		else:
			zoom_output_node = patchbay.find_node(name="ZOOM VoiceEngine", media_class="Stream/Output/Audio")
			if zoom_output_node is None:
				#logger.warning("Zoom output node not found")
				logger.info("Zoom output node not found")
			else:
				i = 0
				# Zoom has LF and RF outputs
				for zoom_output in zoom_output_node.outputs:
					# Speaker may be stereo or mono. If mono, both zoom outputs go to the same speaker input.
					speaker_input = speakers.inputs[i % len(speakers.inputs)]
					linked = False
					# Loop through all the links leading from this output (LF or RF)
					for link in zoom_output.links[:]:
						# If the link is to an audio output device,
						if link.input_port.node.media_class == "Audio/Sink":
							# If it is the one we want, good.
							if link.input_port == speaker_input:
								linked = True
							# Otherwise disconnect it
							else:
								patchbay.destroy_link(link=link)
						# If we didn't find the link we want, create it.
						if not linked:
							patchbay.create_link(zoom_output, speaker_input)
					i += 1

	return failures

def connect_all(patchbay, config):
	"""Connect microphone, OBS, Zoom, and speakers as described in config provided"""
	if getattr(patchbay, "dummy", False):
		return ["Not implemented"]
	if config is None:
		return ["No PERIPHERALS config"]
	failures = []
	failures.extend(create_cable(patchbay))
	failures.extend(connect_peripherals(patchbay, config))
	failures.extend(connect_obs(patchbay))
	failures.extend(connect_zoom(patchbay, config))
	return failures
