from flask import Blueprint, render_template, request, flash, redirect
import logging

from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config, merge_config
from . import menu
from .views import blueprint
from .utils.virtual_cable import patchbay, connect_all

logger = logging.getLogger(__name__)

menu.append((_("Audio"), "/patchbay/"))

@blueprint.route("/patchbay/")
def page_patchbay():
	patchbay.load()
	#patchbay.print()

	# Selected microphone and speakers
	peripherals = get_config("PERIPHERALS")

	# Load the microphone and speaker selectors options
	microphones = []
	speakers = []
	for node in patchbay.nodes:
		if node.media_class == "Audio/Source":
			microphones.append((node.name, node.nick if node.nick else node.name))
		elif node.media_class == "Audio/Sink" and node.name != "To-Zoom":
			speakers.append((node.name, node.nick if node.nick else node.name))

	node_positions = get_config("Patchbay Node Positions")
	for node in patchbay.nodes:
		position = node_positions.get("%s-%d" % (node.name, node.name_serial))
		if position:
			node.style = "position: absolute; left: %dpx; top: %dpx" % tuple(position)
		else:
			node.style = ""

	return render_template("khplayer/patchbay.html",
		peripherals = peripherals,
		microphones = microphones,
		speakers = speakers,
		patchbay = patchbay,
		node_positions = node_positions,
		top = ".."
		)

@blueprint.route("/patchbay/save-config", methods=["POST"])
def page_patchbay_save_config():
	config = {
		"microphone": request.form.get("microphone"),
		"speakers": request.form.get("speakers"),
		}
	put_config("PERIPHERALS", config)
	patchbay.load()
	for failure in connect_all(patchbay, config):
		flash(failure)
	return redirect(".")

@blueprint.route("/patchbay/save-node-pos", methods=["POST"])
def page_patchbay_save_node_pos():
	postdata = request.json
	merge_config("Patchbay Node Positions", {
		postdata["key"]: [postdata["x"], postdata["y"]]
		})
	return ""

@blueprint.route("/patchbay/create-link", methods=["POST"])
def page_patchbay_create_link():
	data = request.json
	patchbay.load()
	patchbay.create_link(int(data['output_port_id']), int(data['input_port_id']))
	return ""

@blueprint.route("/patchbay/destroy-link", methods=["POST"])
def page_patchbay_destroy_link():
	data = request.json
	patchbay.load()
	patchbay.destroy_link(int(data['output_port_id']), int(data['input_port_id']))
	return ""

