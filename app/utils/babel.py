from flask_babel import Babel, gettext, ngettext

def get_locale():
	#return "ru"
	return "en"

def init_babel(app):
	app.babel = babel = Babel(app, locale_selector=get_locale)

