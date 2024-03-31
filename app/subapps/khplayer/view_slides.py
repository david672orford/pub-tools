from flask import current_app, Blueprint, render_template, request, redirect, make_response
from urllib.parse import urlparse, urlencode
import logging

from ...utils.background import progress_callback, progress_response, flash, run_thread
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config
from . import menu
from .views import blueprint
from .utils.scenes import scene_name_prefixes, load_video_url
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

@blueprint.route("/slides/--save-config", methods=["POST"])
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

# NOTE: We originally used .download here, but when we did 
# Turbo failed to enable processing of Turbo-Stream responses.
@blueprint.route("/slides/--download", defaults={"path":None}, methods=["POST"])
@blueprint.route("/slides/<path:path>/--download", methods=["POST"])
def page_slides_folder_download(path):
	client, top = get_client(path)
	assert client is not None
	selected = set(request.form.getlist("selected"))
	run_thread(lambda: download_slides(client, selected))
	return progress_response(None)	# so page doesn't reload

def download_slides(client, selected):
	progress_callback(_("Downloading selected slides..."), cssclass="heading")
	try:
		for file in client.list_image_files():
			if file.id in selected:
				scene_name = request.form.get("scenename-%s" % file.id)
				if file.id.startswith("lank="):
					load_video_url(scene_name, "https://www.jw.org/finder?" + file.id)
				else:
					progress_callback(_("Downloading \"%s\"..." % file.filename))
					filename = client.get_file(file)
					major_mimetype = file.mimetype.split("/")[0]
					scene_name_prefix = scene_name_prefixes.get(major_mimetype)
					obs.add_media_scene(
						scene_name_prefix + " " + request.form.get("scenename-%s" % file.id),
						major_mimetype,
						filename,
						)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Failed to add slide images."), cssclass="error", last_message=True)
	else:
		progress_callback(_("✔ All selected slides added."), cssclass="success", last_message=True)

@blueprint.route("/slides/--reload", defaults={"path":None}, methods=["GET","POST"])
@blueprint.route("/slides/<path:path>/--reload", methods=["POST"])
def page_slides_reload(path):
	path = request.path.removesuffix("--reload")
	#print("path:", path)
	blueprint.cache.delete("slides-%s" % path)
	return redirect(".")

