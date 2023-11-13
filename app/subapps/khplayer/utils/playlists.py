import os, json, base64, re, io
from tempfile import NamedTemporaryFile
import sqlite3
from zipfile import ZipFile
from PIL import Image

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

	@staticmethod
	def make_thumbnail_dataurl(zipreader, filename, mimetype):
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

	# Load any files which have an image file extension
	def load_generic_zip(self):
		self.folder_name = " - ".join(["Zipfile"] + self.path)
		image_count = 0
		path = "/".join(self.path)
		if len(path) > 0:
			path += "/"
		#print("match path:", path)
		for file in self.zipreader.infolist():
			#print("file.filename:", file.filename)
			if file.filename.startswith(path):
				inside_path = file.filename[len(path):]
				#print("inside_path:", inside_path)
				if file.is_dir():
					inside_path = inside_path[:-1]
					if len(inside_path) > 0:
						#print("keep folder:", file.filename, inside_path)
						self.folders.append(PlaylistItem(id=file.filename, filename=inside_path))
				elif not "/" in inside_path:
					m = re.search(r"\.([a-zA-Z0-9]+)$", inside_path)
					if m:
						mimetype = self.extmap.get(m.group(1).lower())
						if mimetype:
							self.files.append(PlaylistItem(id=file.filename, filename=inside_path, mimetype=mimetype,
								thumbnail_url = self.make_thumbnail_dataurl(self.zipreader, file.filename, mimetype),
								))
							image_count += 1

	# Load images from a playlist shared from JW Library
	def load_jwlplaylist(self, manifest):
		self.folder_name = manifest.get("name")
		dbfile = self.zipreader.read("userData.db")
		with NamedTemporaryFile() as fh:
			fh.write(dbfile)
			fh.flush()
			conn = sqlite3.connect(fh.name)
			cur = conn.cursor()
			for label, filepath, mimetype, thumbnailfilepath in cur.execute("""
					select Label, FilePath, MimeType, ThumbnailFilePath
						from PlaylistItem, PlaylistItemIndependentMediaMap, IndependentMedia
						where PlaylistItem.PlaylistItemId = PlaylistItemIndependentMediaMap.PlaylistItemId
							and PlaylistItemIndependentMediaMap.IndependentMediaId = IndependentMedia.IndependentMediaId;
					"""):
				self.files.append(PlaylistItem(id=filepath, filename=label, mimetype=mimetype,
					thumbnail_url = self.make_thumbnail_dataurl(self.zipreader, thumbnailfilepath, "image/jpeg"),
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
			cur = conn.cursor()
			if len(self.path) == 0:		# Table of contents
				self.folder_name = publication["title"]
				for documentid, title, filepath, mimetype in cur.execute("""
						select Document.DocumentId, Document.Title, Multimedia.Filepath, Multimedia.Mimetype
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							group by Document.DocumentId
						"""):
					self.folders.append(PlaylistItem(id=documentid, filename=title,
						thumbnail_url = self.make_thumbnail_dataurl(contents, filepath, mimetype) if mimetype.startswith("image/") else None,
						))
			else:
				cur.execute("select Title from Document where DocumentId = %d" % int(self.path[0]))
				self.folder_name = cur.fetchone()[0]
				for filepath, mimetype in cur.execute("""
						select Multimedia.Filepath, Multimedia.Mimetype
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							where Document.DocumentId = %d
						""" % int(self.path[0])):
					self.files.append(PlaylistItem(id="contents:"+filepath, filename=filepath, mimetype=mimetype,
						thumbnail_url = self.make_thumbnail_dataurl(contents, filepath, mimetype),
						))

	def list_folders(self):
		return self.folders

	def list_image_files(self):
		return self.files

	def download(self, file):
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

