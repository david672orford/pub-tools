import os
from urllib.parse import urlparse, urlencode
import logging

from flask import current_app, Blueprint, render_template, request, redirect, make_response

from ...utils.background import progress_callback, progress_response, flash, run_thread
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config
from ...utils.media_cache import make_media_cachefile_name
from . import menu
from .views import blueprint
from .utils.scenes import load_video_url, load_video_file, load_image_file
from .utils.controllers import obs, ObsError
from .utils.gdrive import GDriveClient
from .utils.playlists import ZippedPlaylist
from .utils.httpfile import RemoteZip

logger = logging.getLogger(__name__)

menu.append((_("Slides"), "/slides/"))

# Form for entering the Google Drive sharing URL
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

# Target of configuration form
@blueprint.route("/slides/--save-config", methods=["POST"])
def page_slides_save_config():
	form = ConfigForm(None, request.form)
	if not form.validate():
		return redirect(".?action=configuration&" + urlencode(form))
	put_config("GDRIVE", form)
	return redirect(".")

# List files in a folder
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

# Refresh a folder's file list
@blueprint.route("/slides/--reload", defaults={"path":None}, methods=["GET","POST"])
@blueprint.route("/slides/<path:path>/--reload", methods=["POST"])
def page_slides_reload(path):
	path = request.path.removesuffix("--reload")
	#print("path:", path)
	blueprint.cache.delete("slides-%s" % path)
	return redirect(".")

# Download button target
# NOTE: We originally used .download as the filename here, but when we did
# Turbo failed to enable processing of Turbo-Stream responses.
@blueprint.route("/slides/--download", defaults={"path":None}, methods=["POST"])
@blueprint.route("/slides/<path:path>/--download", methods=["POST"])
def page_slides_folder_download(path):
	client, top = get_client(path)
	assert client is not None
	selected = set(request.form.getlist("selected"))
	run_thread(lambda: download_slides(client, selected))
	return progress_response(None)	# so page doesn't reload

# Get the Gdrive ID number of the root from the configured Gdrive sharing URL
def get_root_gdrive_id():
	config = get_config("GDRIVE")
	url = config.get("url")
	if url is not None:
		return urlparse(url).path.split("/")[-1]
	return None

# Create a Google Drive client for the indicated path within the configured sharing link
def get_client(path:str):
	client = id = parent_id = zip_filename = None

	# If the path is not empty, take ID from first element with a filename
	# (which will be a zip file) or failing that, from the last element.
	if path is not None:
		path = path.split("/")
		top = "/".join([".."] * (len(path)+1))
		for i in range(len(path)):
			#print(f"path[{i}] = '{path[i]}'")
			parts = path[i].split("=",1)
			if len(parts) == 2:
				id, zip_filename = parts
				path = path[i+1:]
				if parent_id is None:
					parent_id = get_root_gdrive_id()
					assert parent_id is not None
				break
			else:
				parent_id = path[i]
		else:
			id = path[-1]

	# If the path is empty, get the Gdrive ID of the root from the configuration.
	else:
		id = get_root_gdrive_id()
		top = ".."

	#print(f"parent_id={parent_id}, id={id}, zip_filename={zip_filename}, path={path}")

	if id is not None:
		media_cachedir = current_app.config["MEDIA_CACHEDIR"]
		gdrive_cachedir = current_app.config["GDRIVE_CACHEDIR"]

		# If the ID has a .zip extension, build the Gdrive download URL and open it as a remote playlist
		if zip_filename is not None:
			url = f"https://drive.google.com/uc?id={id}"
			#url = f"https://lh3.googleusercontent.com/{id}"
			print("Zip URL:", url)


			client = ZippedPlaylist(
				gdrive_folder_id = parent_id,
				zip_reader = RemoteZip(url, cachekey=id, cachedir=gdrive_cachedir),
				zip_filename = zip_filename,
				path = path,
				cachedir = media_cachedir,
				)

		# Otherwise it is a Gdrive folder
		else:
			client = GDriveClient(
				id,
				thumbnails = True,
				cachedir = media_cachedir,
				)

	return client, top

# Background thread to download slides
# Use the supplied Google Drive client instance to download the items with the indicated ID numbers.
def download_slides(client, selected):
	progress_callback(_("Downloading selected slides..."), cssclass="heading")
	try:
		for file in client.list_image_files():
			if file.id in selected:
				scene_name = request.form.get("scenename-%s" % file.id)

				# A link to a video on JW.ORG
				if file.id.startswith("https://"):
					save_as = make_media_cachefile_name(file.filename, file.mimetype, client.make_uuid(file))
					thumbnail_url = client.download_thumbnail(file, save_as)
					load_video_url(None, file.id, thumbnail_url=thumbnail_url, close=False)

				# An image or video on Google Drive whether inside a zip file or not
				else:
					# FIXME: We have to keep these messages the same as those in utils/scenes.py.
					if file.mimetype.startswith("image/"):
						progress_callback(_("Loading image \"%s\"...") % scene_name, cssclass="heading")
					elif file.mimetype.startswith("video/"):
						progress_callback(_("Loading video \"%s\"...") % scene_name, cssclass="heading")
					else:
						progress_callback(_("Unsupported file type: \"%s\" (%s)") % (file.filename, file.mimetype))

					save_as = make_media_cachefile_name(file.filename, file.mimetype, client.make_uuid(file))
					if not os.path.exists(save_as):
						progress_callback(_("Downloading \"%s\" from Google Drive..." % (file.filename or file.title)))
						client.download_file(file, save_as, callback=progress_callback)

					if file.mimetype.startswith("image/"):
						load_image_file(scene_name, save_as)
					else:
						thumbnail_file = client.download_thumbnail(file, save_as)
						load_video_file(scene_name, save_as, thumbnail_file=thumbnail_file)

	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Failed to add slide images."), cssclass="error", last_message=True)
	else:
		progress_callback(_("✔ All selected slides added."), cssclass="success", last_message=True)

