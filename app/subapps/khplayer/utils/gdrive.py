#
# Simple client for downloading files from Google Drive. Does not log in. To
# use it you create a sharing URL (to share with "anyone with the link") and
# extract the ID from it.
#
# Common Google Drive URL patterns:
#
# What you get when you share a folder:
#  https://drive.google.com/drive/folders/{id}?usp=sharing
# What the browser retrieves when you download a file:
#  https://drive.google.com/uc?export=download&id={id}
# Reportedly you can get image thumbnails like this:
#  https://drive.google.com/thumbnail?id={id}&sz=w{width}-h{height}
# This is what we actually observed for thumbnails:
#  https://lh3.googleusercontent.com/u/0/d/{id}=w400-h380-p-k-rw-v1-nu-iv1
# Reportedly you can embed a folder view in an <iframe> using one of these URLs:
#  https://drive.google.com/embeddedfolderview?id={id}#list
#  https://drive.google.com/embeddedfolderview?id={id}#grid
#
import os, json, re, base64, codecs
import os.path
from time import time
import logging

import requests
import lxml.etree
import lxml.html

logger = logging.getLogger(__name__)

class GDriveClient:
	def __init__(self, path_to:list, path_within:list, thumbnails:bool=False, debug:bool=False):
		self.folder_id = path_to[-1]
		self.thumbnails = thumbnails
		self.debug = debug

		# Put the ID into a sharing URL and retrieve the HTML page
		self.session = requests.Session()
		url = f"https://drive.google.com/drive/folders/{self.folder_id}?usp=sharing"
		response = self.session.get(url, stream=True)
		root = lxml.etree.parse(
			self.IterAsFile(response.iter_content()),
			parser = lxml.etree.HTMLParser(encoding=response.encoding),
			).getroot()

		# If debugging mode is on, save the HTML page to a file in the current directory
		if self.debug:
			text = lxml.html.tostring(root, encoding="UNICODE")
			with open("gdrive.html", "w") as fh:
				fh.write(text)

		# The name of the folder is in the <title> tag
		self.folder_name = root.find(".//title").text

		# Find the JSON object which contains the list of files in this folder.
		#
		# Extraction approach from:
		#   https://github.com/wkentaro/gdown/
		# Correct decoding from:
		#   https://stackoverflow.com/questions/990169/how-do-convert-unicode-escape-sequences-to-unicode-characters-in-a-python-string
		#
		data = None
		for script in root.iterfind(".//script"):
			if script.text is not None and "_DRIVE_ivd" in script.text:
				# Find single-quoted strings
				js_iter = re.compile(r"'((?:[^'\\]|\\.)*)'").finditer(script.text)
				item = next(js_iter).group(1)
				assert item == "_DRIVE_ivd", item
				item = next(js_iter).group(1)
				decoded = codecs.escape_decode(item)[0].decode("utf-8")
				data = json.loads(decoded)
				break
		assert data is not None, "_DRIVE_ivd not found"

		# Save the JSON blob pretty printed alongside the HTML
		if self.debug:
			with open("gdrive.json", "w") as fh:
				json.dump(data, fh, indent=4, ensure_ascii=False)

		# * If the folder is empty, data[0] will be null
		# * If the folder is not empty, data[0] will contain a list of files
		# * Each file entry:
		#   * 0 -- GDrive ID of this file
		#   * 1 -- One-element array containing something that looks like another Gdrive ID
		#   * 2 -- The filename
		#   * 3 -- The MIME type
		#   * 13 -- The size in byte
		#   * The rest of the array is mainly nulls and numbers like 0 and 1 with a few
		#   * things that look like timestamps and a URL to view the file thrown in.
		self.folders = []
		self.image_files = []
		if data[0] is not None:
			for file in data[0]:
				if self.debug:
					print("gdrive file:", file[0], file[2], file[3], file[13])
				id = file[0]

				# Subfolder
				if file[3] in ("application/vnd.google-apps.folder", "application/zip", "application/x-zip"):
					self.folders.append(self.GFile(file, None))

				# Image file
				elif file[3].startswith("image/"):
					self.image_files.append(self.GFile(file, self))

				# Video file
				elif file[3].startswith("video/"):
					# Thumbnail disabled because it is the first frame which is generally black in videos from JW.ORG
					self.image_files.append(self.GFile(file, None))

				# PDF Document
				elif file[3] == "application/pdf":
					self.image_files.append(self.GFile(file, self))

				# Other file types (which we skip)
				else:
					pass

	class GFile:
		def __init__(self, file, client):
			self.id = file[0]
			self.title = file[2]
			self.filename = file[2]
			self.mimetype = file[3]
			self.file_size = file[13]
			self.thumbnail_data = None

			if client is not None and client.thumbnails is not None:
				# This is what the web interface uses:
				# url = f"https://lh3.googleusercontent.com/u/0/d/{id}=w400-h380-p-k-rw-v1-nu-iv1"
				# But this gives the original aspect ratio:
				url = f"https://lh3.googleusercontent.com/u/0/d/{self.id}=w400"
				response = client.session.get(url)
				self.thumbnail_data = response.content

		@property
		def thumbnail_url(self):
			if self.thumbnail_data is None:
				return None
			return "data:{mimetype};base64,{data}".format(
				mimetype = "image/jpeg",
				data = base64.b64encode(self.thumbnail_data).decode("utf-8"),
				)

	class IterAsFile:
		"""Wrap an iterator so we can call .read() on it"""
		def __init__(self, iterator):
			self.iterator = iterator
		def read(self, size=None):
			chunk = next(self.iterator, None)
			if chunk is None:
				return ""
			return chunk

	def list_folders(self):
		"""Get the list of objects representing the subfolders"""
		return self.folders

	def list_image_files(self):
		"""Get the list of objects representing the images files"""
		return self.image_files

	def make_uuid(self, file):
		return file.id

	def download_thumbnail(self, file, save_as):
		if file.thumbnail_data is None:
			return None
		save_as = os.path.splitext(save_as)[0] + ".jpg"
		with open(save_as + ".tmp", "wb") as fh:
			fh.write(file.thumbnail_data)
		os.rename(save_as + ".tmp", save_as)
		return save_as

	def download_file(self, file, save_as, callback=None):
		"""Download file identified by GFile obj"""
		url = f"https://drive.google.com/uc?export=download&id={file.id}"
		response = self.session.get(url, stream=True)
		with open(save_as + ".tmp", "wb") as fh:
			total_recv = 0
			last_callback = 0
			for chunk in response.iter_content(chunk_size=0x10000):
				fh.write(chunk)
				total_recv += len(chunk)
				logger.debug("%d byte chunk, %s of %s bytes received", len(chunk), total_recv, file.file_size)
				if callback is not None:
					now = time()
					if (now - last_callback) >= 0.5 or total_recv == file.file_size:
						callback("{total_recv} of {total_expected}", total_recv=total_recv, total_expected=file.file_size)
						last_callback = now
		os.rename(save_as + ".tmp", save_as)
		return save_as
