from flask import current_app, request, redirect
from sqlalchemy.orm.attributes import flag_modified
from urllib.parse import urlencode
import re
import logging

from ....models import db, Config

logger = logging.getLogger(__name__)

# Wrap app.config so that Wtforms can load and save from it as if it were a DB object.
# The form field names have an upper-case first part and a lower-case second part.
# The two parts represent two dict levels in config.py, like this:
# OBS_WEBSOCKET_hostname -> app.config["OBS_WEBSOCKET"]["hostname"]
class ConfWrapper:
	splitter = re.compile(r"^([A-Z_]+)_([a-z_]+)$")

	# Pull requested value from app.config
	def __getattr__(self, name):
		key1, key2 = self.splitter.match(name).groups()
		return current_app.config.get(key1,{}).get(key2,"")

	def __setattr__(self, name, value):
		key1, key2 = self.splitter.match(name).groups()
		self.set_dict_value(key1, key2, value)

	def set_dict_value(self, key1, key2, value):

		# Copy back into app.config
		current_app.config.get(key1,dict())[key2] = value

		# Also copy into DB so change will persist across app restarts
		conf = Config.query.filter_by(name=key1).one_or_none()
		if conf is None:
			conf = Config(name=key1, data={})
			db.session.add(conf)
		conf.data[key2] = value
		flag_modified(conf, "data")

# Called from POST handlers to validate form data and save it to the DB
def config_saver(form_class):
	config = ConfWrapper()
	form = form_class(formdata=request.form, obj=config)
	if form.validate():
		logger.info("Saving configuration")
		form.populate_obj(config)
		db.session.commit()
		return True, redirect(".")
	else:
		logger.info("Configuration form validation failed")
		return False, redirect(".?" + urlencode(form.data))

# Update values in a dict in the configuration
def config_update_dict(key1, dict_obj):
	config = ConfWrapper()
	for key2, value in dict_obj.items():
		config.set_dict_value(key1, key2, value)
	db.session.commit()

