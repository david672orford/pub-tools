import logging

from ....utils.babel import gettext as _

logger = logging.getLogger(__name__)

def link_nodes(patchbay, source, sink, exclusive=False):
	logger.info("Make sure %s is linked to %s", source.name, sink.name)
	i = 0
	for output in source.outputs:
		linked = False
		for link in output.links:
			if link.input_port is sink.inputs[i]:
				logger.info("%s already linked to %s", source.name, sink.name)
				linked = True
			else:
				logger.info("Unlinking %s from %s", source.name, link.input_port.node.name)
				patchbay.destroy_link(link=link)
		if not linked:
			logger.info("Linking %s to %s", source.name, sink.name)
			patchbay.create_link(source.outputs[i], sink.inputs[i])
		i += 1
	if exclusive:
		i = 0
		for input in sink.inputs:
			for link in input.links:
				if not link.output_port is source.outputs[i]:
					logger.info("Removing spurious link from %s to %s", link.output_port.node.name, sink.name)
			i += 1

def connect_all(patchbay, config):
	"""Connect microphone, OBS, Zoom, and speakers as described in config provided"""
	failures = []

	if (microphone_name := config.get("microphone")) is None:
		failures.append("No microphone selected")
	if (speakers_name := config.get("speakers")) is None:
		failures.append("No speakers selected")
	if len(failures) > 0:
		return failures

	microphone = speakers = obs_input = obs_vcam = zoom_input = zoom_output = None
	obs_monitors = []
	for node in patchbay.nodes:
		if node.name == microphone_name:
			microphone = node
		elif node.name == speakers_name:
			speakers = node
		elif node.name == "OBS":
			if node.media_class == "Stream/Input/Audio":
				obs_input = node
		elif node.name == "OBS-Monitor":
			obs_monitors.append(node)
		elif node.name == "obs-vcam":
			if node.media_class == "Audio/Source":
				obs_vcam = node
		elif node.name == "ZOOM VoiceEngine":
			if node.media_class == "Stream/Input/Audio":
				zoom_input = node
			elif node.media_class == "Stream/Output/Audio":
				zoom_output = node

	if microphone is None:
		failures.append("Selected microphone not found")
	if speakers is None:
		failures.append("Selected speakers not found")
	if obs_input is None:
		failures.append("OBS input not found")
	if obs_vcam is None:
		failures.append(_("OBS virtual camera not started or audio-vcam.lua not installed"))
	if zoom_input is None:
		failures.append(_("Zoom not running (audio input not found)"))
	if zoom_output is None:
		failures.append(_("Zoom not running (audio output not found)"))

	if obs_input is not None:
		link_nodes(patchbay, microphone, obs_input, exclusive=True)
	if obs_vcam is not None and zoom_input is not None:
		link_nodes(patchbay, obs_vcam, zoom_input, exclusive=True)
	for obs_monitor in obs_monitors:
		link_nodes(patchbay, obs_monitor, speakers)
	if zoom_output is not None:
		link_nodes(patchbay, zoom_output, speakers)

	for node in [obs_vcam, zoom_output, speakers] + obs_monitors:
		if node is not None:
			node.set_mute(False)
			node.set_volume(1.0)

	return failures
