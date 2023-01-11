import json, re
from flask import current_app, request, render_template, redirect, flash
from wtforms import Form, StringField, IntegerField, SelectField, URLField, EmailField, validators
from sqlalchemy.orm.attributes import flag_modified
from urllib.parse import urlencode

from ...models import db, Config
from .views import blueprint
from .utils import obs, ObsError
from .view_patchbay import patchbay
from .cameras import list_cameras, get_camera_dev
from .virtual_cable import connect_peripherals

# Wrap app.config so the Wtforms can load and save from it as if it were a DB object.
# The form field names have an upper-case first part and a lower-case second part.
# The two parts represent two dict levels in config.py, like this:
# OBS_WEBSOCKET_hostname -> app.config["OBS_WEBSOCKET"]["hostname"]
class ConfWrapper:
	splitter = re.compile(r"^([A-Z_]+)_([a-z_]+)$")

	# Pull requested value from app.config
	def __getattr__(self, name):
		key1, key2 = self.splitter.match(name).groups()
		return current_app.config.get(key1,{}).get(key2,"")

	# Copy back into app.config
	def __setattr__(self, name, value):
		key1, key2 = self.splitter.match(name).groups()
		current_app.config[key1][key2] = value

		# Also copy into DB so change will persist across app restarts
		conf = Config.query.filter_by(name=key1).one_or_none()
		if conf is None:
			conf = Config(name=key1, data={})
			db.session.add(conf)
		conf.data[key2] = value
		flag_modified(conf, "data")

class ConfigForm(Form):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Load the microphone and speaker selectors options
		patchbay.load()
		microphones = []
		speakers = []
		for node in patchbay.nodes:
			if node.media_class == "Audio/Source":
				microphones.append((node.name, node.nick))
			elif node.media_class == "Audio/Sink":
				speakers.append((node.name, node.nick))
		self.PERIPHERALS_microphone.choices = microphones
		self.PERIPHERALS_speakers.choices = speakers

		# Load the camera selector options
		cameras = []
		for dev_node, display_name in list_cameras():
			cameras.append(display_name)
		self.PERIPHERALS_camera.choices = cameras

	OBS_WEBSOCKET_hostname = StringField("Hostname")
	OBS_WEBSOCKET_port = IntegerField("Port", [validators.NumberRange(min=1024, max=65535)])
	OBS_WEBSOCKET_password = StringField("Password")

	JW_STREAM_url = URLField("URL", [validators.URL()])
	resolutions = ((234, "416x234"), (360, "640x360"), (540, "960x540"), (720, "1280x720"))
	JW_STREAM_preview_resolution = SelectField("Preview Resolution", choices=resolutions, coerce=int)
	JW_STREAM_download_resolution = SelectField("Download Resolution", choices=resolutions, coerce=int)

	ZOOM_username = EmailField("Username", [validators.Email()])
	ZOOM_password = StringField("Password")
	ZOOM_meetingid = StringField("Meeting ID")

	PERIPHERALS_camera = SelectField("Camera")
	PERIPHERALS_microphone = SelectField("Microphone")
	PERIPHERALS_speakers = SelectField("Speakers")

@blueprint.route("/config/", methods=["GET"])
def page_config():
	form = ConfigForm(formdata=request.args, obj=ConfWrapper())
	form.validate()
	return render_template("khplayer/config.html", form=form, top = "..")

@blueprint.route("/config/submit", methods=["POST"])
def page_config_submit():
	config = ConfWrapper()
	form = ConfigForm(formdata=request.form, obj=config)
	if form.validate():
		print("Form validated, saving...")

		# Write to app.config and to the DB
		form.populate_obj(config)
		db.session.commit()

		# Microphone or speaker changes
		patchbay.load()
		connect_peripherals(patchbay, current_app.config["PERIPHERALS"])

		# Camera changes
		camera_dev = get_camera_dev()
		if camera_dev is not None:
			obs.reconnect_camera(camera_dev)

		return redirect(".")
	else:
		print("Validation failed")
		return redirect(".?" + urlencode(form.data))

