from flask import current_app, Blueprint, render_template, request, redirect, flash, make_response
from urllib.parse import urlparse, urlencode
from urllib.request import HTTPSHandler, build_opener, Request
import traceback
import logging

from ...utils import progress_callback
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config
from . import menu
from .views import blueprint
from .utils.controllers import obs, ObsError
from .utils.gdrive import GDriveClient, GDriveZip

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

@blueprint.route("/slides/.save-config", methods=["POST"])
def page_slides_save_config():
	form = ConfigForm(None, request.form)
	if not form.validate():
		return redirect(".?action=configuration&" + urlencode(form))
	put_config("GDRIVE", form)
	return redirect(".")

@blueprint.route("/slides/", defaults={"path":None})
@blueprint.route("/slides/<path:path>/")
def page_slides(path):
	client, top = get_client(path)

	if request.args.get("action") == "configuration" or client is None:
		form = ConfigForm(config["url"], request.args)
	else:
		form = None

	return render_template(
		"khplayer/slides.html",
		client = client,
		form = form,
		top = top,
		)

def get_client(path):
	client = id = None
	top = ".."

	if path is None:
		config = get_config("GDRIVE")
		url = config.get("url")
		if url is not None:
			id = urlparse(url).path.split("/")[-1]
	else:
		path = path.split("/")
		id = path[-1]
		top = "/".join([".."] * (len(path)+1))

	print("id:", id)
	if id is not None: 
		cachedir = current_app.config["CACHEDIR"]
		if id.startswith("zip-"):
			client = GDriveZip(id[4:], cachedir=cachedir)
		else:
			client = GDriveClient(id, thumbnails=True, cachedir=cachedir)

	return client, top

@blueprint.route("/slides/.download", defaults={"path":None}, methods=["POST"])
@blueprint.route("/slides/<path:path>/.download", methods=["POST"])
def page_slides_folder_download(path):
	client = get_client(path)[0]
	assert client is not None
	try:
		selected = set(request.form.getlist("selected"))
		for file in client.list_image_files():
			if file.id in selected:
				progress_callback(_("Downloading \"%s\"..." % file.filename))
				filename = client.download(file)
				obs.add_media_scene("□ " + request.form.get("scenename-%s" % file.id), "image", filename)
		progress_callback(_("Slide images loaded"), last_message=True)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add slide images"), last_message=True)
	return redirect(".")

