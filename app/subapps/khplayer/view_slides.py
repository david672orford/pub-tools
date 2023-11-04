from flask import current_app, Blueprint, render_template, request, redirect, flash
from urllib.parse import urlparse, urlencode
import logging

from ...utils import progress_callback
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config
from . import menu
from .views import blueprint
from .utils.controllers import obs
from .utils.gdrive import GDriveClient

logger = logging.getLogger(__name__)

menu.append((_("Slides"), "/slides/"))

class ConfigForm(dict):
	def __init__(self, config, data):
		if config is not None:
			self.update(config)
		if "url" in data:
			self["url"] = data["url"].strip()
	def validate(self):
		u = urlparse(self["url"])
		if u.scheme!="https" or u.netloc!="drive.google.com" or u.query!="usp=sharing":
			flash(_("Not a Google Drive sharing URL"))
			return False
		return True

@blueprint.route("/slides/")
def page_slides():
	config = get_config("GDRIVE")
	files = []
	if "url" in config:
		try:
			files = GDriveClient(config, cachedir=current_app.config["CACHEDIR"]).list_files()
		except Exception as e:
			flash(_("Exception: %s") % e)
	if request.args.get("action") == "configuration" or not "url" in config:
		form = ConfigForm(config, request.args)
	else:
		form = None
	return render_template(
		"khplayer/slides.html",
		files = files,
		form = form,
		top = ".."
		)

@blueprint.route("/slides/save-config", methods=["POST"])
def page_slides_save_config():
	form = ConfigForm(None, request.form)
	if not form.validate():
		return redirect(".?action=configuration&" + urlencode(form))
	put_config("GDRIVE", form)
	return redirect(".")

@blueprint.route("/slides/download", methods=["POST"])
def page_slides_load():
	gdrive = GDriveClient(get_config("GDRIVE"), cachedir=current_app.config["CACHEDIR"])
	files = {}
	for file in gdrive.list_files():
		files[file.id] = file
	for id in request.form.getlist("selected"):
		if id in files:
			progress_callback(_("Downloading \"%s\"..." % files[id].filename))
			filename = gdrive.download(files[id])
			obs.add_media_scene("□ " + request.form.get("scenename-%s" % id), "image", filename)
	return redirect(".")

