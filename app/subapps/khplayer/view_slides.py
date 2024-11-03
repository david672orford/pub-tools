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
from .utils.localdrive import LocalDriveClient
from .utils.gdrive import GDriveClient
from .utils.playlists import ZippedPlaylist
from .utils.httpfile import RemoteZip, LocalZip

logger = logging.getLogger(__name__)

menu.append((_("Slides"), "/slides/"))

# Form for entering the Google Drive sharing URL
class ConfigForm(dict):
	def __init__(self, config, data):
		if config is not None:
			self.update(config)
		if "url" in data:
			self["url"] = data["url"].strip() or None
	def validate(self):
		if self["url"] is None:
			return True
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
	return redirect("--reload")

# List files in a folder
@blueprint.route("/slides/", defaults={"path":None})
@blueprint.route("/slides/<path:path>/")
@blueprint.cache.cached(timeout=900, key_prefix="slides-%s", unless=lambda: request.args.get("action") is not None)
def page_slides(path):
	client, top = get_fs_client(path)

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
	client, top = get_fs_client(path)
	assert client is not None
	selected = set(request.form.getlist("selected"))
	run_thread(lambda: download_slides(client, selected))
	return progress_response(None)	# so page doesn't reload

# Go to the configuration and get the root folder for speaker's slides
# and the client class for connecting to it.
def get_root_folder():
	config = get_config("GDRIVE")
	url = config.get("url")
	if url is not None:
		url = urlparse(url)
		return GDriveClient, url.path.split("/")[-1]
	else:
		return LocalDriveClient, os.path.abspath(os.path.join(current_app.instance_path, "slides"))
	return None, None

# Create a file system client for the indicated path
# Path elements are one of the following:
# * Google Drive ID of a folder
# * Google Drive ID of a zip file plus the filename separated by an equal sign
# The elements are /-separated.
# A path of None indicates the root which will be gotten by calling get_root_folder_id().
def get_fs_client(path:str):

	# Parse the path and set the following following:
	# top -- parent path back to the top
	# path_to -- path clipped to stop at the first zip file (if any)
	# zip_filename -- if last element of path_to[] is a zip file, its name
	# path_within -- list of folders to traverse within the zip file (if any)
	if path is None:
		top = ".."
		path_to = []
		zip_filename = None
		path_within = []
	else:
		path = path.split("/")
		top = "/".join([".."] * (len(path)+1))
		for i in range(len(path)):
			parts = path[i].split("=",1)
			if len(parts) == 2:
				folder_id, zip_filename = parts
				path_to = path[:i] + [folder_id]
				path_within = path[i+1:]
				break
		else:
			path_to = path
			zip_filename = None
			path_within = []

	client_class, root_folder = get_root_folder()
	path_to.insert(0, root_folder)

	print(f"top={repr(top)}, path_to={path_to}, zip_filename={repr(zip_filename)}, path_within={path_within}")

	if path_to[0] is not None:
		media_cachedir = current_app.config["MEDIA_CACHEDIR"]
		gdrive_cachedir = current_app.config["GDRIVE_CACHEDIR"]

		# If the ID is a zip file, build the Gdrive download URL and open it as a remote playlist.
		if zip_filename is not None:
			if client_class is GDriveClient:
				url = f"https://drive.google.com/uc?id={folder_id}"
				#url = f"https://lh3.googleusercontent.com/{folder_id}"
				print("Zip URL:", url)
				zip_reader = RemoteZip(url, cachekey=path_to[-1], cachedir=gdrive_cachedir)
			else:
				zip_reader = LocalZip(os.path.join(*path_to))

			client = ZippedPlaylist(
				path_to,
				path_within,
				zip_reader = zip_reader,
				zip_filename = zip_filename,
				client_class = client_class,
				cachedir = media_cachedir,
				)

		# Otherwise it is a Gdrive folder
		else:
			client = client_class(
				path_to,
				path_within,
				thumbnails = True,
				cachedir = media_cachedir,
				)
	else:
		client = None

	return client, top

# Background thread to download slides
# Use the supplied file system client instance to download the items
# with the indicated ID numbers.
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
						load_image_file(scene_name, save_as, close=False)
					else:
						thumbnail_file = client.download_thumbnail(file, save_as)
						load_video_file(scene_name, save_as, thumbnail_file=thumbnail_file, close=False)

	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Failed to add slide images."), cssclass="error", last_message=True)
	else:
		progress_callback(_("✔ All selected slides added."), cssclass="success", last_message=True)

