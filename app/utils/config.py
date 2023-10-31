from ..models import db, Config
from sqlalchemy.orm.attributes import flag_modified

def get_config(name):
	conf = Config.query.filter_by(name=name).one_or_none()
	if conf is None:
		return {}
	return conf.data

def put_config(name, data):
	conf = Config.query.filter_by(name=name).one_or_none()
	if conf is None:
		conf = Config(name=name)
		db.session.add(conf)
	conf.data = data
	db.session.commit()

def merge_config(name, data):
	conf = Config.query.filter_by(name=name).one_or_none()
	if conf is None:
		conf = Config(name=name, data={})
		db.session.add(conf)
	conf.data.update(data)
	flag_modified(conf, "data")
	db.session.commit()

