import os, json, base64, re, io, sqlite3
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
from urllib.parse import urlencode
import json
from PIL import Image

# Reader for zip files which may contain one or more playlists
# Supported formats:
# * plain zip file: folders are rendered, images files in each folder constitute a playlist
# * .jwlplaylist file: one playlist of images and video links listed in PlaylistItem DB table
# * .jwpub file: each document (generally a talk) a folder containing its multimedia items
class ZippedPlaylist:
	class PlaylistItem:
		def __init__(self, id, filename, mimetype=None, thumbnail_url=None):
			self.id = id
			self.filename = filename
			self.mimetype = mimetype
			self.thumbnail_url = thumbnail_url

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
			self._load_generic_zip()
		elif "userDataBackup" in manifest:
			self._load_jwlplaylist(manifest)
		elif "publication" in manifest:
			self._load_jwpub_playlist(manifest)

	def list_folders(self):
		"""Called from the Jinja2 template to get the list of folders to display"""
		return self.folders

	def list_image_files(self):
		"""Called from the Jinja2 template to get the list of files to display"""
		return self.files

	def get_file(self, file):
		"""Called from view_slides.py to extract a file from the archive"""
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		zipreader = self.zipreader
		id = file.id
		if id.startswith("contents:"):		# double zip
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

	# Any image files found in the zip file will be considered part of the playlist
	# TODO: * Omit directories without image files
	#       * Show first image file as (folder?) thumbnail
	#       * Show the filename of the zip file (from Gdrive) rather than "Zipfile"
	def _load_generic_zip(self):

		# Table of file types to look for in the zip file
		extmap = {
			"jpg": "image/jpeg",
			"png": "image/png",
			"gif": "image/gif",
			"svg": "image/svg+xml",
			}

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
						self.folders.append(self.PlaylistItem(id=file.filename, filename=inside_path
							#thumbnail_url = 
							))
				elif not "/" in inside_path:
					m = re.search(r"\.([a-zA-Z0-9]+)$", inside_path)
					if m:
						mimetype = extmap.get(m.group(1).lower())
						if mimetype:
							self.files.append(self.PlaylistItem(id=file.filename, filename=inside_path, mimetype=mimetype,
								thumbnail_url = self._make_thumbnail_dataurl(self.zipreader, file.filename, mimetype),
								))
							image_count += 1

	# Load image list from a playlist shared from JW Library (.jwlplaylist).
	def _load_jwlplaylist(self, manifest):
		self.folder_name = manifest.get("name")
		dbfile = self.zipreader.read("userData.db")
		with NamedTemporaryFile() as fh:
			fh.write(dbfile)
			fh.flush()
			conn = sqlite3.connect(fh.name)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			for row in cur.execute("""
					select Label, FilePath, MimeType, DocumentId as MepsDocumentId, KeySymbol, Track, IssueTagNumber, ThumbnailFilePath
						from PlaylistItem
						left join PlaylistItemIndependentMediaMap using(PlaylistItemId)
						left join IndependentMedia using(IndependentMediaId)
						left join PlaylistItemLocationMap using(PlaylistItemId)
						left join Location using(LocationId);
					"""):
				row = dict(row)
				print("jwlplaylist item:", json.dumps(row, indent=4, ensure_ascii=False))
				if row["FilePath"] and row["MimeType"] == "image/jpeg":
					id = row["FilePath"]
				else:
					id = self._make_video_id(row)
				print("jwpub playlist item id:", id)
				print()
				self.files.append(self.PlaylistItem(
					id = id,
					filename = row["Label"],
					mimetype = row["MimeType"],
					thumbnail_url = self._make_thumbnail_dataurl(self.zipreader, row["ThumbnailFilePath"], "image/jpeg"),
					))

	# Load image list from a JWPUB file such as the Public Talk Media Playlist (S-34mp_U.jwpub)
	def _load_jwpub_playlist(self, manifest):
		publication = manifest["publication"]
		contents = self.zipreader.open_zipfile("contents")
		dbfile = contents.read(publication["fileName"])
		with NamedTemporaryFile() as fh:
			fh.write(dbfile)
			fh.flush()
			conn = sqlite3.connect(fh.name)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()

			# Table of contents (lists talks)
			if len(self.path) == 0:
				self.folder_name = publication["title"]
				for row in cur.execute("""
						select DocumentId, Title, FilePath as ThumbnailFilePath, MimeType as ThumbnailMimeType
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia on DocumentMultimediaId=Multimedia.MultimediaId
							group by Document.DocumentId
						"""):
					row = dict(row)
					print("jwpub document item:", json.dumps(row, indent=4, ensure_ascii=False))
					self.folders.append(self.PlaylistItem(
						id = row["DocumentId"],
						filename = row["Title"],
						thumbnail_url = self._make_thumbnail_dataurl(contents, row["ThumbnailFilePath"], row["ThumbnailMimeType"]),
						))
			else:						# Document (a particular talk and its media)
				cur.execute("select Title from Document where DocumentId = ?", (int(self.path[0]),))
				self.folder_name = cur.fetchone()[0]
				for row in cur.execute("""
						select DocumentId,
								Multimedia.MultimediaId,
								Multimedia.FilePath, Multimedia.MimeType,
								Multimedia.KeySymbol, Multimedia.Track, Multimedia.IssueTagNumber, MultiMedia.MepsDocumentId,
								Multimedia2.MultimediaId as ThumbnailMultimediaId, Multimedia2.FilePath as ThumbnailFilePath, Multimedia2.MimeType as ThumbnailMimeType
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							inner join Multimedia as Multimedia2 on Multimedia.LinkMultimediaId=Multimedia2.MultimediaId
							where Document.DocumentId = ?
						""", (int(self.path[0]),)):
					row = dict(row)

					print("jwpub playlist item:", json.dumps(row, indent=4, ensure_ascii=False))
					if row["MimeType"].startswith("image/"):
						id = "contents:"+row["FilePath"]
						filename = row["FilePath"]
					else:
						id = self._make_video_id(row)
						filename = "%s %02d" % (row["KeySymbol"], row["Track"])
					print("jwpub playlist item id:", id)
					print()

					self.files.append(self.PlaylistItem(
						id = id,
						filename = filename,
						mimetype = row["MimeType"],
						thumbnail_url = self._make_thumbnail_dataurl(contents, row["ThumbnailFilePath"], row["ThumbnailMimeType"]),
						))

	# For .jwlplaylist and .jwpub playlists
	# Given a row from the playlist's Sqlite DB, return a JW.ORG sharing URL.
	#
	# Items which are multimedia attachments to a print publication may not
	# have their own sharing URL, so we leave the hostname out to show it is
	# not an actual JW.ORG sharing URL.
	@staticmethod
	def _make_video_id(row):

		# A video as a media item of a songbook or talk outline
		if row["KeySymbol"] and row["Track"]:
			return "https:///finder?" + urlencode({"pub": row["KeySymbol"], "track": row["Track"], "issue": row["IssueTagNumber"]})

		# Link to a video in the JW Broadcasting player
		if row["KeySymbol"]:
			return "https://www.jw.org/finder?" + urlencode({"lank": "pub-{KeySymbol}_{Track}_VIDEO".format(**row)})

		# A video on a standalone player page
		if row["MepsDocumentId"] and row["Track"]:
			return "https://www.jw.org/finder?" + urlencode({"lank": "docid-{MepsDocumentId}_{Track}_VIDEO".format(**row)})

		raise AssertionError("Can't make URL: %s" % row)

	# For all playlist formats
	# Read an image from the zip file and turn it into a data URL.
	# If it is large, scale it down first.
	@staticmethod
	def _make_thumbnail_dataurl(zipreader, filename, mimetype):
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

