import json, re
from flask import current_app, request, render_template, redirect, flash
from wtforms import Form, StringField, IntegerField, validators
from sqlalchemy.orm.attributes import flag_modified

from ...models import db, Config
from .views import blueprint

class ConfigForm(Form):
	OBS_WEBSOCKET_hostname = StringField("Hostname")
	OBS_WEBSOCKET_port = IntegerField("Port")
	JW_STREAM_url = StringField("URL")
	ZOOM_username = StringField("Username")
	ZOOM_password = StringField("Password")
	ZOOM_meetingid = StringField("Meeting ID")

# Wrap app.config so the Wtforms can load and save from it as if it were a DB object.
# The form field names have an upper-case first part and a lower-case second part.
# This specify two levels in app.config:
# OBS_WEBSOCKET_hostname -> app.config["OBS_WEBSOCKET"]["hostname"]
class ConfWrapper:
	splitter = re.compile(r"^([A-Z_]+)_([a-z_]+)$")

	# Pull requested value from app.config
	def __getattr__(self, name):
		key1, key2 = self.splitter.match(name).groups()
		return current_app.config[key1][key2]

	# Copy back into app.config
	def __setattr__(self, name, value):
		print("Set:", name, value)
		key1, key2 = self.splitter.match(name).groups()
		current_app.config[key1][key2] = value

		# Also copy into DB so change will persist accross app restarts
		conf = Config.query.filter_by(name=key1).one_or_none()
		print("conf:", conf)
		if conf is None:
			conf = Config(name=key1, data={})
			db.session.add(conf)
		conf.data[key2] = value
		flag_modified(conf, "data")

@blueprint.route("/config/")
def page_config():
	form = ConfigForm(formdata=request.form, obj=ConfWrapper())
	return render_template("khplayer/config.html", form=form, top = "..")

@blueprint.route("/config/submit", methods=["POST"])
def page_config_submit():
	config = ConfWrapper()
	form = ConfigForm(formdata=request.form, obj=config)
	form.populate_obj(config)
	db.session.commit()
	return redirect(".")

