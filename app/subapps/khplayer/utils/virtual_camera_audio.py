import logging

from ...utils.babel import gettext as _

logger = logging.getLogger(__name__)

def link_nodes(patchbay, source, sink):
	i = 0
	for output in source.outputs:
		linked = False
		for link in output.links:
			if link.input_port is zoom_input[i]:
				logger.info("%s already linked to zoom", source.name)
				linked = True
			else:
				logger.info("Unlinking %s from %s", source.name, link.input_port.node.name)
				patchbay.destroy_link(link=link)
			if not linked:
				logger.info("Linking %s to %s", source.name, sink.name)
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
		elif node.name == "OBS Virtual Camera":
			if node.media_class == "Audio/Source":
				vcam = node
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
		failures.append(_("OBS virtual camera not started"))
	if zoom_input is None:
		failures.append(_("Zoom not running (audio input not found)"))
	if zoom_output is None:
		failures.append("Zoom not running (audio output not found)"))

	if len(failures) == 0:
		link_nodes(patchbay, obs_input, microphone)
		link_nodes(patchbay, obs_vcam, zoom_input)
		for obs_monitor in obs_monitors:
			link_nodes(patchbay, obs_monitor, speakers)
		link_nodes(patchbay, zoom_output, speakers)

	return failures
