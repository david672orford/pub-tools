import os

from flask import current_app
from flask_babel import Babel, gettext, ngettext
from babel.messages.pofile import read_po
from babel.messages.mofile import write_mo

def get_locale():
	return current_app.config["UI_LANGUAGE"]

def init_babel(app):
	app.babel = Babel(app, locale_selector=get_locale)

def compile_babel_catalogs():
	translations = os.path.join(os.path.dirname(__file__), "..", "translations")
	for language in ("ru",):
		pofile = os.path.join(translations, language, "LC_MESSAGES", "messages.po")
		mofile = os.path.join(translations, language, "LC_MESSAGES","messages.mo")
		if not os.path.exists(mofile) or os.path.getmtime(mofile) < os.path.getmtime(pofile):
			with open(pofile) as fh:
				catalog = read_po(fh)
			with open(mofile, "wb") as fh:
				write_mo(fh, catalog)
