# Create a virtual audio cable to connect the output of OBS to the microphone
# input of Zoom. We also connect the microphone and speakers to this cable.

import sys, os, types, re
from subprocess import run, PIPE
from time import sleep

def create_cable(patchbay):
	for name, media_class in (
		("To-Zoom", "Audio/Sink"),
		("From-OBS", "Audio/Source/Virtual"),
		):
		print(f"Creating {name}...")
		node = patchbay.find_node_by_name(name)
		if node is None:
			run(["pactl",
				"load-module", "module-null-sink",
				"media.class=" + media_class,
				"sink_name=" + name,
				"sink_properties=device.description=" + name,
				"channel_map=mono",
				], stdout=PIPE, check=True)
			print("  Created.")
		else:
			print(f"  {name} already exists")
	
	# Give them a chance to settle
	sleep(.1)

	# Connect them
	patchbay.load()
	patchbay.create_link("To-Zoom:monitor_MONO", "From-OBS:input_MONO")

def destroy_cable(patchbay):
	for name in ("From-OBS", "To-Zoom"):
		node = patchbay.find_node_by_name(name)
		run(["pw-cli", "destroy", str(node.id)], check=True)

def connect_peripherals(patchbay, config):
	# Connect the microphone specified in config.py to the input of the virtual
	# audio cable which connects the output of OBS to the micriphone input of Zoom.
	if "microphone" in config:
		microphone_node = patchbay.find_node_by_name(config["microphone"])
		for port in microphone_node.outputs:
			patchbay.create_link(port, "From-OBS:input_MONO")
	
	# Connect each set of speakers specified in config.py to the output of the
	# same virtual audio cable. This allows those physically present to hear
	# what OBS is sending to Zoom.
	if "speakers" in config:
		speakers_node = patchbay.find_node_by_name(config["speakers"])
		for port in speakers_node.inputs:
			patchbay.create_link("To-Zoom:monitor_MONO", port)

def reconnect_obs(patchbay):
	virtual_cable_node = patchbay.find_node_by_name("To-Zoom")
	virtual_cable_input = virtual_cable_node.inputs[0]

	# Ensure OBS monitor outputs are connected to the virtual cable and nothing else.
	for node in patchbay.nodes:
		if node.name == "OBS-Monitor":
			print("Node:", node.name)
			for output in node.outputs:
				print(" Output:", output.name)
				linked = False
				for link in output.links:
					print(" Link:", link)
					if link.input_port is virtual_cable_input:
						linked = True
					else:
						print("  Incorrect link")
						patchbay.destroy_link(link=link)
				if not linked:
					patchbay.create_link(output, virtual_cable_input)

def connect_all(patchbay, config):
	create_cable(patchbay)
	connect_peripherals(patchbay, config)
	reconnect_obs(patchbay)

