import os, json, base64, re, io, sqlite3
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
from PIL import Image
from urllib.parse import urlencode

class PlaylistItem:
	def __init__(self, id, filename, mimetype=None, thumbnail_url=None):
		self.id = id
		self.filename = filename
		self.mimetype = mimetype
		self.thumbnail_url = thumbnail_url

class ZippedPlaylist:
	extmap = {
		"jpg": "image/jpeg",
		"png": "image/png",
		"gif": "image/gif",
		"svg": "image/svg+xml",
		}

	def __init__(self, zipreader, path, cachedir="cache"):
		self.zipreader = zipreader
		self.path = path
		self.cachedir = cachedir

		self.folder_name = None
		self.files = []
		self.folders = []

		try:
			manifest = json.loads(self.zipreader.read("manifest.json"))
		except KeyError:
			manifest = None

		if manifest is None:
			self.load_generic_zip()
		elif "userDataBackup" in manifest:
			self.load_jwlplaylist(manifest)
		elif "publication" in manifest:
			self.load_talk_playlist(manifest)

	# Load any files which have an image file extension
	# TODO: Skip directories without image files.
	#       Show first image file as thumbnail.
	def load_generic_zip(self):
		self.folder_name = " - ".join(["Zipfile"] + self.path)
		image_count = 0
		path = "/".join(self.path)
		if len(path) > 0:
			path += "/"
		for file in self.zipreader.infolist():
			if file.filename.startswith(path):
				inside_path = file.filename[len(path):]
				if file.is_dir():
					inside_path = inside_path[:-1]
					if len(inside_path) > 0:
						self.folders.append(PlaylistItem(id=file.filename, filename=inside_path
							#thumbnail_url = 
							))
				elif not "/" in inside_path:
					m = re.search(r"\.([a-zA-Z0-9]+)$", inside_path)
					if m:
						mimetype = self.extmap.get(m.group(1).lower())
						if mimetype:
							self.files.append(PlaylistItem(id=file.filename, filename=inside_path, mimetype=mimetype,
								thumbnail_url = self.make_thumbnail_dataurl(self.zipreader, file.filename, mimetype),
								))
							image_count += 1

	# Load images from a playlist shared from JW Library (.jwlplaylist).
	def load_jwlplaylist(self, manifest):
		self.folder_name = manifest.get("name")
		dbfile = self.zipreader.read("userData.db")
		with NamedTemporaryFile() as fh:
			fh.write(dbfile)
			fh.flush()
			conn = sqlite3.connect(fh.name)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			for row in cur.execute("""
					select Label, FilePath, MimeType, DocumentId as MepsDocumentId, KeySymbol, Track, ThumbnailFilePath
						from PlaylistItem
						left join PlaylistItemIndependentMediaMap using(PlaylistItemId)
						left join IndependentMedia using(IndependentMediaId)
						left join PlaylistItemLocationMap using(PlaylistItemId)
						left join Location using(LocationId);
					"""):
				row = dict(row)
				print("jwlplaylist:", row)
				if row["FilePath"]:			# FIXME: or MimeType?
					id = row["FilePath"]
				else:
					id = self.make_video_id(row)
				print("id:", id)
				self.files.append(PlaylistItem(id=id, filename=row["Label"], mimetype=row["MimeType"],
					thumbnail_url = self.make_thumbnail_dataurl(self.zipreader, row["ThumbnailFilePath"], "image/jpeg"),
					))

	# Load images from a talk playlist such as S-34mp_U.jwpub
	def load_talk_playlist(self, manifest):
		publication = manifest["publication"]
		contents = self.zipreader.open_zipfile("contents")
		dbfile = contents.read(publication["fileName"])
		with NamedTemporaryFile() as fh:
			fh.write(dbfile)
			fh.flush()
			conn = sqlite3.connect(fh.name)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			if len(self.path) == 0:		# Table of contents
				self.folder_name = publication["title"]
				for row in cur.execute("""
						select DocumentId, Title, FilePath, MimeType
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							group by Document.DocumentId
						"""):
					self.folders.append(PlaylistItem(id=row["DocumentId"], filename=row["Title"],
						thumbnail_url = self.make_thumbnail_dataurl(contents, row["FilePath"], row["MimeType"]),
						))
			else:
				cur.execute("select Title from Document where DocumentId = ?", (int(self.path[0]),))
				self.folder_name = cur.fetchone()[0]
				for row in cur.execute("""
						select FilePath, MimeType, KeySymbol, Track, MultiMedia.MepsDocumentId
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							where Document.DocumentId = ?
						""", (int(self.path[0]),)):
					row = dict(row)
					print("jwpub playlist:", row)
					if row["MimeType"].startswith("image/"):
						id = "contents:"+row["FilePath"]
					else:
						id = self.make_video_id(row)
					print("id:", id)
					self.files.append(PlaylistItem(id=id, filename=row["FilePath"], mimetype=row["MimeType"],
						thumbnail_url = self.make_thumbnail_dataurl(contents, row["FilePath"], row["MimeType"]),
						))

	@staticmethod
	def make_thumbnail_dataurl(zipreader, filename, mimetype):
		if not mimetype.startswith("image/"):
			return None
		data = zipreader.read(filename)
		if len(data) > 12000:
			image = Image.open(io.BytesIO(data))
			# Scale to our thumbnail.large size
			image.thumbnail((184, 105))
			# Save as JPEG. Why do we need to set quality so high?
			save_to = io.BytesIO()
			image.save(save_to, format="jpeg", quality=85)
			data = save_to.getvalue()
			mimetype = "image/jpeg"
		return "data:{mimetype};base64,{data}".format(
			mimetype = mimetype,
			data = base64.b64encode(data).decode('utf-8'),
			)

	# Given a row from the playlist's Sqlite DB, return a fragment of mediator query string.
	@staticmethod
	def make_video_id(row):
		if row["KeySymbol"]:
			return urlencode({"lank": "pub-{KeySymbol}_{Track}_VIDEO".format(**row)})
		elif row["MepsDocumentId"]:
			return urlencode({"lank": "docid-{MepsDocumentId}_{Track}_VIDEO".format(**row)})
		else:
			raise AssertionError("Can't make URL: %s" % row)

	# Called from the Jinja2 template to get the list of folders to display
	def list_folders(self):
		return self.folders

	# Called from the Jinja2 template to get the list of files to display
	def list_image_files(self):
		return self.files

	# Called from view_slides.py to extract a file from the archive
	def get_file(self, file):
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		zipreader = self.zipreader
		id = file.id
		if id.startswith("contents:"):
			zipreader = zipreader.open_zipfile("contents")
			id = id[9:]
		with zipreader.open(id) as fh1:
			with open(cachefile, "wb") as fh2:
				while True:
					chunk = fh1.read(0x10000) # 64k
					if not chunk:
						break
					fh2.write(chunk)
		return cachefile

