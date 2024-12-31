from flask import current_app, render_template, request, redirect
import logging

from ...utils.background import flash
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config, merge_config
from . import menu
from .views import blueprint
from .utils.pipewire import Patchbay

if current_app.config["PATCHBAY"] == "virtual-cable":
	from .utils.virtual_cable import connect_all
else:
	from .utils.virtual_camera_audio import connect_all

logger = logging.getLogger(__name__)

menu.append((_("Audio"), "/patchbay/"))

class AudioDevices:
	"""Backend for GUI controls of virtual audio cable"""
	def __init__(self, patchbay):
		self.peripherals = get_config("PERIPHERALS")
		self.microphones = []
		self.speakers = []
		for node in patchbay.nodes:
			if node.media_class == "Audio/Source":
				self.microphones.append((node.name, node.nick if node.nick else node.name))
			elif node.media_class == "Audio/Sink" and node.name != "To-Zoom":
				self.speakers.append((node.name, node.nick if node.nick else node.name))

class Positioner:
	"""Automatically position nodes in patchbay"""
	def __init__(self):
		class PositionerColumn:
			def __init__(self, x, step, reservations=[]):
				self.x = x
				self.y = 0
				self.step = step
				self.reservations = {}
				for reservation in reservations:
					self.reservations[reservation] = self.y
					self.y += self.step
		self.columns = {
			"Left": PositionerColumn(10, 85),
			"Center": PositionerColumn(300, 150, reservations=["ZOOM VoiceEngine", "To-Zoom", "From-OBS"]),
			"Right": PositionerColumn(750, 110),
			}

	def get_node_column(self, node):
		cl = node.media_class.split("/")
		if node.name == "ZOOM VoiceEngine":
			column_name = {
				"Output": "Center",
				"Input": "Right",
				}.get(cl[1])
		elif node.name == "To-Zoom":
			column_name = "Center"
		elif node.media_class == "Stream/Output/Audio":		# OBS outputs
			column_name = "Left"
		elif len(cl) == 2 and cl[0] == "Audio":
			column_name = {
				"Source": "Left",		# Audio/Source (microphone)
				"Sink": "Right",		# Audio/Sink (speakers)
				}.get(cl[1], "Center")
		else:
			column_name = "Center"

		#print(node, column_name)
		return self.columns[column_name]

	def record_node(self, node, position):
		column = self.get_node_column(node)
		x, y = position
		column.y = y + column.step

	def place_node(self, node):
		column = self.get_node_column(node)
		reservation = column.reservations.get(node.name)
		#print("reservtion:", reservation)
		if reservation is not None:
			y = reservation
		else:
			y = column.y
			column.y += column.step
		return column.x, y

@blueprint.route("/patchbay/")
def page_patchbay():
	patchbay = Patchbay()
	patchbay.load()
	#patchbay.print()

	if request.args.get("action") == "reset":
		node_positions = {}
		put_config("Patchbay Node Positions", node_positions)
	else:
		node_positions = get_config("Patchbay Node Positions")

	positioner = Positioner()
	for node in patchbay.nodes:
		if "Audio" in node.media_class and not node.is_vu_meter:
			position = node_positions.get("%s-%d" % (node.name, node.name_serial))
			if position is not None:
				positioner.record_node(node, position)
			else:
				position = positioner.place_node(node)
			node.style = "position: absolute; left: %dpx; top: %dpx" % tuple(position)

	return render_template("khplayer/patchbay.html",
		patchbay = patchbay,
		devices = AudioDevices(patchbay),
		node_positions = node_positions,
		top = ".."
		)

@blueprint.route("/patchbay/reconnect", methods=["POST"])
def page_patchbay_reconnect():
	config = {
		"microphone": request.form.get("microphone"),
		"speakers": request.form.get("speakers"),
		}
	put_config("PERIPHERALS", config)
	patchbay = Patchbay()
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
	patchbay = Patchbay()
	patchbay.load()
	patchbay.create_link(int(data['output_port_id']), int(data['input_port_id']))
	return ""

@blueprint.route("/patchbay/destroy-link", methods=["POST"])
def page_patchbay_destroy_link():
	data = request.json
	patchbay = Patchbay()
	patchbay.load()
	patchbay.destroy_link(int(data['output_port_id']), int(data['input_port_id']))
	return ""
