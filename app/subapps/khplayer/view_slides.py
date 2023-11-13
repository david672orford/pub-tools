from flask import current_app, Blueprint, render_template, request, redirect, flash, make_response
from urllib.parse import urlparse, urlencode
from urllib.request import HTTPSHandler, build_opener, Request
import traceback
import logging

from ...utils import progress_callback, async_flash
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config
from . import menu
from .views import blueprint
from .utils.controllers import obs, ObsError
from .utils.gdrive import GDriveClient
from .utils.playlists import ZippedPlaylist
from .utils.httpfile import RemoteZip

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
@blueprint.cache.cached(timeout=900, key_prefix="slides-%s", unless=lambda: request.args.get("action") is not None)
def page_slides(path):
	client, top = get_client(path)

	if request.args.get("action") == "configuration" or client is None:
		form = ConfigForm(get_config("GDRIVE"), request.args)
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
		top = "/".join([".."] * (len(path)+1))
		for i in range(len(path)):
			if path[i].endswith(".zip"):
				id = path[i]
				path = path[i+1:]
				break
		else:
			id = path[-1]

	if id is not None: 
		media_cachedir = current_app.config["MEDIA_CACHEDIR"]
		gdrive_cachedir = current_app.config["GDRIVE_CACHEDIR"]
		if id.endswith(".zip"):
			id = id[:-4]
			url = f"https://drive.google.com/uc?id={id}"
			#url = f"https://lh3.googleusercontent.com/{id}"
			print("Zip URL:", url)
			client = ZippedPlaylist(RemoteZip(url, cachedir=gdrive_cachedir, cachekey=id), path=path, cachedir=media_cachedir)
		else:
			client = GDriveClient(id, thumbnails=True, cachedir=media_cachedir)

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
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add slide images"), last_message=True)
		return redirect(".?action=flash")	# FIXME: action=flash is hack to get flash() past cache
	return redirect(".")

@blueprint.route("/slides/.reload", defaults={"path":None}, methods=["GET","POST"])
@blueprint.route("/slides/<path:path>/.reload", methods=["POST"])
def page_slides_reload(path):
	path = request.path.removesuffix(".reload")
	print("path:", path)
	blueprint.cache.delete("slides-%s" % path)
	return redirect(".")


