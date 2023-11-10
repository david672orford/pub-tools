import os, json, re, base64, codecs
import requests
import lxml.etree
import lxml.html
from remotezip import RemoteZip
from tempfile import NamedTemporaryFile
import sqlite3

class GFile:
	def __init__(self, file, thumbnail_url):
		self.id = file[0]
		self.filename = file[2]
		self.mimetype = file[3]
		self.thumbnail_url = thumbnail_url

class IterAsFile:
	def __init__(self, iterator):
		self.iterator = iterator
	def read(self, size=None):
		chunk = next(self.iterator, None)
		if chunk is None:
			return ""
		return chunk

class GDriveClient:
	def __init__(self, id, thumbnails=False, cachedir="cache", debug=False):
		self.cachedir = cachedir
		self.debug = debug

		url = "https://drive.google.com/drive/folders/{id}?usp=sharing".format(id=id)
		self.session = requests.Session()
		response = self.session.get(url, stream=True)
		self.root = lxml.etree.parse(IterAsFile(response.iter_content()), parser=lxml.etree.HTMLParser(encoding=response.encoding)).getroot()

		if self.debug:
			text = lxml.html.tostring(self.root, encoding="UNICODE")
			with open("gdrive.html", "w") as fh:
				fh.write(text)

		self.folder_name = self.root.find(".//title").text

		# Find the JSON object which contains the list of files.
		#
		# Extraction approach from:
		#   https://github.com/wkentaro/gdown/
		# Correct decoding from:
		#   https://stackoverflow.com/questions/990169/how-do-convert-unicode-escape-sequences-to-unicode-characters-in-a-python-string
		#
		data = None
		for script in self.root.iterfind(".//script"):
			if script.text is not None and "_DRIVE_ivd" in script.text:
				# Find single-quoted strings
				js_iter = re.compile(r"'((?:[^'\\]|\\.)*)'").finditer(script.text)
				item = next(js_iter).group(1)
				assert item == "_DRIVE_ivd", item
				item = next(js_iter).group(1)
				decoded = codecs.escape_decode(item)[0].decode("utf-8")
				data = json.loads(decoded)
				if self.debug:
					with open("gdrive.json", "w") as fh:
						json.dump(data, fh, indent=4, ensure_ascii=False)
				break
		assert data is not None, "_DRIVE_ivd not found"

		# * If the folder is empty, data[0] will be null
		# * If the folder is not empty, data[0] will contain a list of files
		# * Each file entry:
		#   * 0 -- GDrive ID of this file
		#   * 1 -- One-element array containing what looks like another Gdrive ID
		#   * 2 -- The filename
		#   * 3 -- The MIME type
		#   * The rest of the array is mainly nulls and numbers like 0 and 1 with a few
		#   * things that look like timestamps and a URL to view the file thrown in.
		self.files = []
		if data[0] is not None:
			for file in data[0]:
				id = file[0]
				if thumbnails:
					response = self.session.get("https://lh3.googleusercontent.com/u/0/d/{id}=w400-h380-p-k-rw-v1-nu-iv1".format(id=id))
					thumbnail_url = "data:{mimetype};base64,{data}".format(
						mimetype = response.headers.get("Content-Type","").split(";")[0],
						data = base64.b64encode(response.content).decode('utf-8'),
						)
				else:
					thumbnail_url = None
				self.files.append(GFile(file, thumbnail_url))

	# Get an iterator over a list of objects representing the subfolders.
	def list_folders(self):
		for file in self.files:
			if file.mimetype in ("application/vnd.google-apps.folder", "application/zip"):
				yield file
		
	# Get an iterator over a list of objects representing the images files
	# at the top level of this Google Drive folder.
	def list_image_files(self):
		for file in self.files:
			if file.mimetype.startswith("image/"):
				yield file

	def download(self, file):
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		url = "https://drive.google.com/uc?export=download&id=%s" % file.id
		response = self.session.get(url)
		with open(cachefile, "wb") as fh:
			fh.write(response.content)
		return cachefile

class GDriveZipMember:
	def __init__(self, file, mimetype=None, thumbnail_url=None):
		self.id = file.filename
		self.filename = file.filename
		self.mimetype = mimetype
		self.thumbnail_url = thumbnail_url

class GDriveZip:
	def __init__(self, id, cachedir="cache"):
		self.cachedir = cachedir
		self.folder_name = "Playlist"

		url = "https://drive.google.com/uc?export=download&id=%s" % id
		url = "http://raven.lan/~david/sample.jwlplaylist"
		print(url)
		self.remote = RemoteZip(url)

		self.files = {}
		is_playlist = False
		for file in self.remote.infolist():
			if file.is_dir():
				fileobj = GDriveZipMember(file)
				self.files[fileobj.id] = fileobj
			elif file.filename.endswith(".jpg"):
				fileobj = GDriveZipMember(file, mimetype="image/jpeg")
				self.files[fileobj.id] = fileobj
			elif file.filename == "userData.db":
				is_playlist = True

		if is_playlist:
			dbfile = self.remote.read("userData.db")
			with NamedTemporaryFile() as fh:
				fh.write(dbfile)
				fh.flush()
				conn = sqlite3.connect(fh.name)
				cur = conn.cursor()
				for filepath, label, thumbnailfilepath in cur.execute("""
						select FilePath, Label, ThumbnailFilePath
							from PlaylistItem, PlaylistItemIndependentMediaMap, IndependentMedia
							where PlaylistItem.PlaylistItemId = PlaylistItemIndependentMediaMap.PlaylistItemId
								and PlaylistItemIndependentMediaMap.IndependentMediaId = IndependentMedia.IndependentMediaId;
						"""):
					print("row:", filepath, label, thumbnailfilepath)
					file = self.files[filepath]
					file.thumbnail_url = "data:{mimetype};base64,{data}".format(
						mimetype = "image/jpeg",
						data = base64.b64encode(self.remote.read(thumbnailfilepath)).decode('utf-8'),
						)
					file.filename = label
					
		self.files = self.files.values()

		for file in self.files:
			if file.mimetype.startswith("image/") and file.thumbnail_url is None:
				file.thumbnail_url = "data:{mimetype};base64,{data}".format(
					mimetype = "image/jpeg",
					data = base64.b64encode(self.remote.read(file.filename)).decode('utf-8'),
					)

	def list_folders(self):
		for file in self.files:
			if file.mimetype is None:
				yield file

	def list_image_files(self):
		for file in self.files:
			if file.mimetype is not None:
				yield file

	def download(self, file):
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		with self.remote.open(file.id) as fh1:
			with open(cachefile, "wb") as fh2:
				while True:
					chunk = fh1.read(0x10000) # 64k
					if not chunk:
						break
					fh2.write(chunk)
		return cachefile

