import os, json, base64, re, io, sqlite3
from tempfile import NamedTemporaryFile
from zipfile import ZipFile
from urllib.parse import urlencode
import json
from fnmatch import fnmatch
from PIL import Image

from .gdrive import GDriveClient

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

	def __init__(self, parent_id:str, zip_reader, zip_filename:str, path, cachedir="cache", debuglevel=10):
		self.parent_id = parent_id			# Google Drive ID of folder containing this zip file
		self.zip_reader = zip_reader		# Zipfile compatible object
		self.path = path					# path to folder within zipfile
		self.zip_filename = zip_filename	# filename of the .zip file
		self.cachedir = cachedir			# directory into which to download media files
		self.debuglevel = debuglevel

		self.folder_name = None
		self.files = []
		self.folders = []
		self.parent_reader = None

		try:
			manifest = json.loads(self.zip_reader.read("manifest.json"))
		except KeyError:
			manifest = None
		if self.debuglevel > 0:
			print("Playlist manifest:", json.dumps(manifest, indent=4, ensure_ascii=False))
			print()

		if manifest is None:
			self._load_generic_zip()
		elif "userDataBackup" in manifest:
			self._load_jwlplaylist(manifest)
		elif "publication" in manifest:
			self._load_jwpub_playlist(manifest)
		else:
			raise AssertionError("Unsupported playlist format")

	def list_folders(self):
		"""Called from the Jinja2 template to get the list of folders to display"""
		return self.folders

	def list_image_files(self):
		"""Called from the Jinja2 template to get the list of files to display"""
		return self.files

	def download_file(self, file, save_as):
		"""Called from view_slides.py to extract a file from the archive"""
		id = file.id

		if id.startswith("gdrive:"):
			id = id[7:]
			for gfile in self.parent_reader.list_image_files():
				if gfile.id == id: 
					return self.parent_reader.download_file(gfile, save_as)
			else:
				raise AssertionError("File not found in parent Gdrive folder")

		zip_reader = self.zip_reader
		if file.id.startswith("contents:"):		# double zip
			zip_reader = zip_reader.open_zipfile("contents")
			id = id[9:]

		with zip_reader.open(id) as fh1:
			with open(save_as + ".tmp", "wb") as fh2:
				while True:
					chunk = fh1.read(0x10000) # 64k
					if not chunk:
						break
					fh2.write(chunk)

		os.rename(save_as + ".tmp", save_as)

		return save_as

	# Any image files found in the zip file will be considered part of the playlist
	# TODO: * Omit directories without image files
	#       * Show first image file as (folder?) thumbnail
	def _load_generic_zip(self):

		# Table of file types to look for in the zip file
		extmap = {
			"jpg": "image/jpeg",
			"png": "image/png",
			"gif": "image/gif",
			"svg": "image/svg+xml",
			}

		# Folder name is a breadcrumb-like path
		if len(self.path) == 0:
			self.folder_name = self.zip_filename
		else:
			self.folder_name = self.path[-1]

		ls_path = "/".join(self.path)
		if len(ls_path) > 0:
			ls_path += "/"
		if self.debuglevel > 0:
			print("zip ls_path:", ls_path)

		for file in self.zip_reader.infolist():

			# If file is within the indicated directory,
			if file.filename.startswith(ls_path):

				# File's relative path from that directory
				inside_path = file.filename[len(ls_path):]
				if self.debuglevel > 0:
					print("zip inside_path:", inside_path)

				if file.is_dir():
					inside_path = inside_path[:-1]
					# If not the indicated directory itself,
					if len(inside_path) > 0:
						self.folders.append(self.PlaylistItem(
							id = file.filename[:-1],
							filename = inside_path,
							#thumbnail_url = 
							))

				elif not "/" in inside_path:
					# Extract the filename extension
					m = re.search(r"\.([a-zA-Z0-9]+)$", inside_path)
					if m:
						mimetype = extmap.get(m.group(1).lower())
						if mimetype:
							self.files.append(self.PlaylistItem(
								id = file.filename,
								filename = inside_path,
								mimetype = mimetype,
								thumbnail_url = self._make_thumbnail_dataurl(self.zip_reader, file.filename, mimetype),
								))

	# Load image list from a playlist shared from JW Library (.jwlplaylist).
	def _load_jwlplaylist(self, manifest):
		#self.folder_name = manifest.get("name")
		self.folder_name = self.zip_filename
		dbfile = self.zip_reader.read("userData.db")
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

				filename = None
				if row["FilePath"] and row["MimeType"] == "image/jpeg":
					id = row["FilePath"]		# some kind of UUID
				else:
					id, filename = self._make_video_id(row)

				if filename is None:
					filename = row["Label"]		# by default, the JW.ORG filename

				self.files.append(self.PlaylistItem(
					id = id,
					filename = filename,
					mimetype = row["MimeType"],
					thumbnail_url = self._make_thumbnail_dataurl(self.zip_reader, row["ThumbnailFilePath"], "image/jpeg"),
					))

				print("jwpub playlist item id:", id)
				print()

	# Load image list from a JWPUB file such as the Public Talk Media Playlist (S-34mp_U.jwpub)
	def _load_jwpub_playlist(self, manifest):
		publication = manifest["publication"]
		contents = self.zip_reader.open_zipfile("contents")
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
						select DocumentId, Title,
								Multimedia.FilePath as ThumbnailFilePath, Multimedia.MimeType as ThumbnailMimeType
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							group by Document.DocumentId
						"""):
					row = dict(row)
					print("jwpub document item:", json.dumps(row, indent=4, ensure_ascii=False))
					self.folders.append(self.PlaylistItem(
						id = row["DocumentId"],
						filename = row["Title"],
						thumbnail_url = self._make_thumbnail_dataurl(contents, row["ThumbnailFilePath"], row["ThumbnailMimeType"]),
						))

			# Document (a particular talk and its media)
			else:
				docid = int(self.path[0])
				cur.execute("select Title from Document where DocumentId = ?", (docid,))
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
							left outer join Multimedia as Multimedia2 on Multimedia.LinkMultimediaId=Multimedia2.MultimediaId
							where Document.DocumentId = ?
						""", (docid,)):
					row = dict(row)
					print("jwpub playlist item:", json.dumps(row, indent=4, ensure_ascii=False))

					if row["MimeType"].startswith("image/"):
						id = "contents:"+row["FilePath"]
						filename = row["FilePath"]
					else:
						id, filename = self._make_video_id(row)
						if filename is None:
							filename = "%s %02d" % (row["KeySymbol"], row["Track"])

					if row["ThumbnailFilePath"]:
						thumbnail_url = self._make_thumbnail_dataurl(contents, row["ThumbnailFilePath"], row["ThumbnailMimeType"])
					elif row["FilePath"] and row["MimeType"] == "image/jpeg":
						thumbnail_url = self._make_thumbnail_dataurl(contents, row["FilePath"], row["MimeType"])
					else:
						thumbnail_url = None

					self.files.append(self.PlaylistItem(
						id = id,
						filename = filename,
						mimetype = row["MimeType"],
						thumbnail_url = thumbnail_url,
						))

					print("jwpub playlist item id:", id)
					print()

	# For .jwlplaylist and .jwpub playlists
	# Given a row from the playlist's Sqlite DB, return a JW.ORG sharing URL.
	#
	# Items which are multimedia attachments to a print publication may not
	# have their own sharing URL, so we leave the hostname out to show it is
	# not an actual JW.ORG sharing URL.
	def _make_video_id(self, row):

		# A video as a media item of a songbook or talk outline
		if row["KeySymbol"] and row["Track"]:

			if self.parent_reader is None:
				self.parent_reader = GDriveClient(self.parent_id, cachedir=self.cachedir)
			pattern = f"{row['KeySymbol']}_*_{row['Track']:02}_r*P.mp4"
			print("pattern:", pattern)
			for gfile in self.parent_reader.list_image_files():
				print("file:", gfile.filename)
				if fnmatch(gfile.filename, pattern):
					return f"gdrive:{gfile.id}", gfile.filename

			return "https:///finder?" + urlencode({"pub": row["KeySymbol"], "track": row["Track"], "issue": row["IssueTagNumber"]}), None

		# FIXME: not reached
		# Link to a video in the JW Broadcasting player
		if row["KeySymbol"]:
			return "https://www.jw.org/finder?" + urlencode({"lank": "pub-{KeySymbol}_{Track}_VIDEO".format(**row)}), None

		# A video on a standalone player page
		if row["MepsDocumentId"] and row["Track"]:
			return "https://www.jw.org/finder?" + urlencode({"lank": "docid-{MepsDocumentId}_{Track}_VIDEO".format(**row)}), None

		raise AssertionError("Can't make URL: %s" % row)

	# For all playlist formats
	# Read an image from the zip file and turn it into a data URL.
	# If it is large, scale it down first.
	@staticmethod
	def _make_thumbnail_dataurl(zip_reader, filename, mimetype):
		if mimetype is None or not mimetype.startswith("image/"):
			return None
		data = zip_reader.read(filename)
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

