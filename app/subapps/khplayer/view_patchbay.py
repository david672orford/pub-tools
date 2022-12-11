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

	node_positions = Config.query.filter_by(name="Patchbay Node Positions").one_or_none()
	if node_positions is not None:
		node_positions = node_positions.data
		for node in patchbay.nodes:
			position = node_positions.get(node.name)
			print("position:", position)
			if position:
				node.style = "position: absolute; left: %dpx; top: %dpx" % tuple(position)
			else:
				node.style = ""

	return render_template("khplayer/patchbay.html", patchbay=patchbay, node_positions=node_positions, top="..")

@blueprint.route("/patchbay/savepos", methods=["POST"])
def page_patchbay_save_pos():
	data = request.json
	node_positions = Config.query.filter_by(name="Patchbay Node Positions").one_or_none()
	if node_positions is None:
		node_positions = Config(name="Patchbay Node Positions", data={})
		db.session.add(node_positions)
	node_positions.data[data["name"]] = [data["x"], data["y"]]
	flag_modified(node_positions, "data")
	db.session.commit()
	return ""

@blueprint.route("/patchbay/create-link", methods=["POST"])
def page_patchbay_create_link():
	data = request.json
	print(data)
	output_node_id, output_link_id = map(int, data['from'].split("-")[1:])
	input_node_id, input_link_id = map(int, data['to'].split("-")[1:])
	patchbay.create_link(
		output_node_id,
		output_link_id,
		input_node_id,
		input_link_id,
		)
	return ""
