from flask import current_app, Blueprint, render_template, request, redirect, flash
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

@blueprint.route("/slides/")
def page_slides():
	config = get_config("GDRIVE")
	if "url" in config:
		files = GDriveClient(config, cachedir=current_app.config["CACHEDIR"]).list_files()
	else:
		files = []
	return render_template(
		"khplayer/slides.html",
		config2 = config if request.args.get("action") == "configuration" else None,
		files = files,
		top = ".."
		)

@blueprint.route("/slides/save-config", methods=["POST"])
def page_slides_save_config():
	put_config("GDRIVE", {
		"url": request.form.get("url")
		})
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

