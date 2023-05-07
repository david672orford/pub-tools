from flask import Blueprint, render_template, request, redirect, flash
from sqlalchemy.orm.attributes import flag_modified
from time import sleep
import json

from ...models import db, Config
from .views import blueprint
from .pipewire import Patchbay

patchbay = Patchbay()

@blueprint.route("/patchbay/")
def page_patchbay():
	patchbay.load()
	#patchbay.print()

	node_positions = Config.query.filter_by(name="Patchbay Node Positions").one_or_none()
	if node_positions is not None:
		node_positions = node_positions.data
		for node in patchbay.nodes:
			position = node_positions.get("%s-%d" % (node.name, node.name_serial))
			if position:
				node.style = "position: absolute; left: %dpx; top: %dpx" % tuple(position)
			else:
				node.style = ""

	return render_template("khplayer/patchbay.html", patchbay=patchbay, node_positions=node_positions, top="..")

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

