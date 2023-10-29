from flask import current_app, Blueprint, render_template, request, redirect, flash
from wtforms import Form, StringField
from urllib.request import Request, HTTPHandler, HTTPSHandler, build_opener
from urllib.parse import urlparse, parse_qsl, urlencode, unquote
import lxml.html
import os, json, re
import logging

from ...utils import progress_callback
from ...utils.babel import gettext as _
from . import menu
from .views import blueprint
from .utils.controllers import obs
from .utils.config_editor import ConfWrapper, config_saver

logger = logging.getLogger(__name__)

menu.append((_("Slides"), "/slides/"))

class SlidesConfigForm(Form):
	GDRIVE_url = StringField(_("Google Drive Sharing URL"))

class GDriveClient:
	user_agent = "Mozilla/5.0"
	request_timeout = 30

	def __init__(self, config, cachedir="cache", debuglevel=0):
		self.config = config
		self.cachedir = cachedir
		http_handler = HTTPHandler(debuglevel=debuglevel)
		https_handler = HTTPSHandler(debuglevel=debuglevel)
		self.opener = build_opener(http_handler, https_handler)

	def get(self, url, query=None):
		if query:
			url = url + '?' + urlencode(query)
		request = Request(
			url,
			headers={
				"Accept": "text/html, */*",
				#"Accept-Encoding": "gzip",
				"Accept-Language": "en-US",
				"User-Agent": self.user_agent,
				}
			)
		response = self.opener.open(request, timeout=self.request_timeout)
		return response

	def get_html(self, url, query=None):
		response = self.get(url, query=query)
		return lxml.html.parse(response).getroot()

	# Return a list of objects representing the images files at the top
	# level of this Google Drive folder.
	def list_files(self):
		root = self.get_html(self.config["url"])

		#text = lxml.html.tostring(root, encoding="UNICODE")
		#with open("gdrive.html", "w") as fh:
		#	fh.write(text)

		# Parsing approach from:
		# https://github.com/wkentaro/gdown/
		data = None
		for script in root.iterfind(".//script"):
			if script.text is not None and "_DRIVE_ivd" in script.text:
				js_iter = re.compile(r"'((?:[^'\\]|\\.)*)'").finditer(script.text)
				item = next(js_iter).group(1)
				assert item == "_DRIVE_ivd", item
				item = next(js_iter).group(1)
				decoded = item.encode("utf-8").decode("unicode_escape")
				data = json.loads(decoded)

				#with open("gdrive.json", "w") as fh:
				#	json.dump(data, fh, indent=4)

				break

		assert data is not None	

		class GFile:
			def __init__(self, file):
				self.id = file[0]
				self.filename = file[2]
				self.mimetype = file[3]
			@property
			def thumbnail_url(self):
				return "https://drive.google.com/uc?export=download&id=%s" % self.id
			@property
			def download_url(self):
				return "https://drive.google.com/uc?export=download&id=%s" % self.id

		for file in data[0]:
			if file[3].startswith("image/"):
				yield GFile(file)

	def download(self, file):
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		response = self.get(file.download_url)
		with open(cachefile, "wb") as fh:
			while True:
				chunk = response.read(0x10000) # 64k
				if not chunk:
					break
				fh.write(chunk)
		return cachefile

@blueprint.route("/slides/")
def page_slides():
	return render_template(
		"khplayer/slides.html",
		form = SlidesConfigForm(formdata=request.args, obj=ConfWrapper()) if request.args.get("action") == "configuration" else None,
		files = GDriveClient(current_app.config["GDRIVE"], cachedir=current_app.config["CACHEDIR"]).list_files(),
		top = ".."
		)

@blueprint.route("/slides/save-config", methods=["POST"])
def page_slides_save_config():
	ok, response = config_saver(SlidesConfigForm)
	return response

@blueprint.route("/slides/download", methods=["POST"])
def page_slides_load():
	gdrive = GDriveClient(current_app.config["GDRIVE"], cachedir=current_app.config["CACHEDIR"])
	files = {}
	for file in gdrive.list_files():
		files[file.id] = file
	for id in request.form.getlist("selected"):
		if id in files:
			progress_callback(_("Downloading \"%s\"..." % files[id].filename))
			filename = gdrive.download(files[id])
			obs.add_media_scene("□ " + request.form.get("scenename-%s" % id), "image", filename)
	return redirect(".")

