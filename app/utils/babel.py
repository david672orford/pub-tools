from flask import current_app
from flask_babel import Babel, gettext, ngettext

def get_locale():
	return current_app.config["UI_LANGUAGE"]

def init_babel(app):
	app.babel = babel = Babel(app, locale_selector=get_locale)

