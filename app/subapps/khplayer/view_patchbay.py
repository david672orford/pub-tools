from flask import current_app, Blueprint, render_template, request, flash
from wtforms import Form, SelectField
from sqlalchemy.orm.attributes import flag_modified
import logging

from ...models import db, Config
from ...babel import gettext as _
from .views import blueprint, menu
from .utils.virtual_cable import patchbay, connect_all
from .utils.config_editor import ConfWrapper, config_saver

logger = logging.getLogger(__name__)

menu.append((_("Audio"), "/audio/"))

class AudioConfigForm(Form):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Load the microphone and speaker selectors options
		microphones = []
		speakers = []
		for node in patchbay.nodes:
			if node.media_class == "Audio/Source":
				microphones.append((node.name, node.nick if node.nick else node.name))
			elif node.media_class == "Audio/Sink" and node.name != "To-Zoom":
				speakers.append((node.name, node.nick if node.nick else node.name))
		self.PERIPHERALS_microphone.choices = microphones
		self.PERIPHERALS_speakers.choices = speakers

	PERIPHERALS_microphone = SelectField("Microphone")
	PERIPHERALS_speakers = SelectField("Speakers")

@blueprint.route("/patchbay/")
def page_patchbay():
	patchbay.load()
	#patchbay.print()

	form = AudioConfigForm(formdata=request.args, obj=ConfWrapper())

	node_positions = Config.query.filter_by(name="Patchbay Node Positions").one_or_none()
	if node_positions is not None:
		node_positions = node_positions.data
		for node in patchbay.nodes:
			position = node_positions.get("%s-%d" % (node.name, node.name_serial))
			if position:
				node.style = "position: absolute; left: %dpx; top: %dpx" % tuple(position)
			else:
				node.style = ""

	return render_template("khplayer/patchbay.html", form=form, patchbay=patchbay, node_positions=node_positions, top="..")

@blueprint.route("/patchbay/save-config", methods=["POST"])
def page_patchbay_save_config():
	ok, response = config_saver(AudioConfigForm)
	if ok:
		patchbay.load()
		for failure in connect_all(patchbay, current_app.config["PERIPHERALS"]):
			flash(failure)
	return response

@blueprint.route("/patchbay/save-node-pos", methods=["POST"])
def page_patchbay_save_node_pos():
	postdata = request.json
	node_positions = Config.query.filter_by(name="Patchbay Node Positions").one_or_none()
	if node_positions is None:
		node_positions = Config(name="Patchbay Node Positions", data={})
		db.session.add(node_positions)
	node_positions.data[postdata["key"]] = [postdata["x"], postdata["y"]]
	flag_modified(node_positions, "data")
	db.session.commit()
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

