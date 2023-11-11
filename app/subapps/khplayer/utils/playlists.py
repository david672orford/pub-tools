import os
import base64
from tempfile import NamedTemporaryFile
import sqlite3

class PlaylistItem:
	def __init__(self, file, mimetype=None, thumbnail_url=None):
		self.id = file.filename
		self.filename = file.filename
		self.mimetype = mimetype
		self.thumbnail_url = thumbnail_url

class ZippedPlaylist:
	def __init__(self, zipreader, cachedir="cache"):
		self.zipreader = zipreader
		self.folder_name = "Playlist"

		self.files = {}
		is_playlist = False
		for file in self.remote.infolist():
			if file.is_dir():
				fileobj = PlaylistItem(file)
				self.files[fileobj.id] = fileobj
			elif file.filename.endswith(".jpg"):
				fileobj = PlaylistItem(file, mimetype="image/jpeg")
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

