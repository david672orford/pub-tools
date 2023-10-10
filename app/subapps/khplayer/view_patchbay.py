from flask import current_app, Blueprint, render_template, request, redirect, flash
from wtforms import Form, SelectField
from sqlalchemy.orm.attributes import flag_modified
from urllib.parse import urlencode
import logging

from ...models import db, Config
from ...babel import gettext as _
from .views import blueprint, menu
from .virtual_cable import patchbay, connect_all
from .config_wrapper import ConfWrapper

logger = logging.getLogger(__name__)

menu.append((_("Audio"), "/patchbay/"))

class AudioConfigForm(Form):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Load the microphone and speaker selectors options
		microphones = []
		speakers = []
		for node in patchbay.nodes:
			if node.media_class == "Audio/Source":
				microphones.append((node.name, node.nick))
			elif node.media_class == "Audio/Sink":
				speakers.append((node.name, node.nick))
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
	config = ConfWrapper()
	form = AudioConfigForm(formdata=request.form, obj=config)
	if form.validate():
		logger.info("Saving audio config")
		form.populate_obj(config)
		db.session.commit()

		patchbay.load()
		for failure in connect_all(patchbay, current_app.config["PERIPHERALS"]):
			flash(failure)

		return redirect(".")
	else:
		logger.info("Audio config form validation failed")
		return redirect(".?" + urlencode(form.data))

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

