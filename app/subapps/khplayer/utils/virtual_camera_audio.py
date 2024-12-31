import logging

logger = logging.getLogger(__name__)

def find_device(patchbay, config, key, failures):
	if key not in config:
		failures.append("No %s selected in configuration", key)
		return None
	device = patchbay.find_node(name=config[key])
	if device is None:
		failures.append("Selected %s is not connected", key)
		return None
	return device

def link_to_microphone(patchbay, node, microphone):
	for input in node.inputs:
		linked = False
		for link in input.links:
			if link.output_port in microphone.outputs:
				linked = True
			else:
				patchbay.destroy_link(link=link)
		if not linked:
			patchbay.create_link(microphone.outputs[0], input)

def link_to_speakers(patchbay, node, speakers):
	i = 0
	for output in node.outputs:
		linked = False
		for link in output.links:
			if link.input_port is speakers.inputs[i]:
				logger.info("%s already linked to speakers", node.name)
				linked = True
			else:
				logger.info("Unlinking %s from %s", node.name, link.input_port.node.name)
				patchbay.destroy_link(link=link)
		if not linked:
			logger.info("Linking %s to speakers", node.name)
			patchbay.create_link(output, speakers.inputs[i])
		i += 1

def link_to_vcam(patchbay, node):
	pass

def connect_all(patchbay, config):
	"""Connect microphone, OBS, Zoom, and speakers as described in config provided"""
	failures = []

	microphone = find_device(patchbay, config, "microphone", failures)
	speakers = find_device(patchbay, config, "speakers", failures)

	for node in patchbay.nodes:
		if node.name == "OBS":
			if node.media_class == "Stream/Input/Audio":
				link_to_microphone(patchbay, node, microphone)

		elif node.name == "OBS-Monitor":
			link_to_speakers(patchbay, node, speakers)

		elif node.name == "ZOOM VoiceEngine":
			if node.media_class == "Stream/Input/Audio":
				link_to_vcam(patchbay, node)

			elif node.media_class == "Stream/Output/Audio":
				link_to_speakers(patchbay, node, speakers)

	return failures
