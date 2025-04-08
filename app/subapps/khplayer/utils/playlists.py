"""Open media playlists stored in zip files"""

import os
import json
import base64
import re
import io
import sqlite3
import os.path
from tempfile import mkstemp
from zipfile import ZipFile
from urllib.parse import urlencode
import json
from fnmatch import fnmatch
from hashlib import md5
from PIL import Image

#from ....models import Videos
from .mimetypes import extmap

# Reader for zip files which may contain one or more playlists
# Supported formats:
# * plain zip file: folders are rendered, images files in each folder constitute a playlist
# * .jwlplaylist file: one playlist of images and video links listed in PlaylistItem DB table
# * .jwpub file: each document (generally a talk) a folder containing its multimedia items
class ZippedPlaylist:
	def __init__(self, path_to:list, path_within:list, zip_reader, zip_filename:str, client_class, cachedir="cache", debuglevel=0):
		self.path_to = path_to
		self.path = path_within						# path to folder within zipfile
		self.zip_reader = zip_reader				# Zipfile compatible object
		self.zip_filename = zip_filename			# filename of the .zip file
		self.client_class = client_class
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

	class PlaylistItem:
		def __init__(self, id, title, filename, mimetype=None, file_size=None, thumbnail=(None,None,None)):
			self.id = id
			self.title = title
			self.filename = filename
			self.mimetype = mimetype			# None for folders
			self.file_size = file_size			# None for folders

			self.thumbnail_data = None
			(zip_reader, filename, self.thumbnail_mimetype) = thumbnail
			if self.thumbnail_mimetype is not None and self.thumbnail_mimetype.startswith("image/"):
				self.thumbnail_data = zip_reader.read(filename)
				if len(self.thumbnail_data) > 12000:
					image = Image.open(io.BytesIO(self.thumbnail_data))
					# Scale to our thumbnail.large size
					image.thumbnail((184, 105))
					# Save as JPEG. Why do we need to set quality so high?
					save_to = io.BytesIO()
					image.save(save_to, format="jpeg", quality=85)
					self.thumbnail_data = save_to.getvalue()
					self.thumbnail_mimetype = "image/jpeg"

		@property
		def thumbnail_url(self):
			if self.thumbnail_data is None:
				return None
			return "data:{mimetype};base64,{data}".format(
				mimetype = self.thumbnail_mimetype,
				data = base64.b64encode(self.thumbnail_data).decode("utf-8"),
				)
		def __str__(self):
			return f"<PlaylistItem id={self.id} title={repr(self.title)} filename={repr(self.filename)} file_size={repr(self.file_size)}>"

	def list_folders(self):
		"""Called from the Jinja2 template to get the list of folders to display"""
		return self.folders

	def list_image_files(self):
		"""Called from the Jinja2 template to get the list of files to display"""
		return self.files

	def make_uuid(self, file):
		return self.path_to[-1] + "-" + md5(file.id.encode("utf-8")).hexdigest()

	def download_thumbnail(self, file, save_as):
		"""Download thumbnail of specified file alongside save_as, return filename"""
		if file.thumbnail_data is None:
			return None
		save_as = os.path.splitext(save_as)[0] + ".jpg"
		with open(save_as + ".tmp", "wb") as fh:
			fh.write(file.thumbnail_data)
		os.rename(save_as + ".tmp", save_as)
		return save_as

	def download_file(self, file, save_as, callback=None):
		"""Called from view_slides.py to extract a file from the archive"""
		id = file.id

		if id.startswith("gdrive:"):
			id = id[7:]
			for gfile in self.parent_reader.list_image_files():
				if gfile.id == id:
					return self.parent_reader.download_file(gfile, save_as, callback=callback)
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

	# Load image list from supported images files found in an generic zip archive
	def _load_generic_zip(self):

		if len(self.path) == 0:
			self.folder_name = self.zip_filename
		else:
			self.folder_name = self.path[-1]

		# Set search_dir to a prefix ending in slash which we can use to filter
		# the output of .infolist() down to the subdirectory we want. For the
		# root, the prefix will be an empty string.
		search_folder = "/".join(self.path)
		if len(search_folder) > 0:
			search_folder += "/"
		if self.debuglevel > 0:
			print("zip search_folder:", search_folder)

		# Go through the tree of files and directories within the zip
		folders_included = set()
		for file in self.zip_reader.infolist():
			if file.filename.startswith(search_folder) and not file.is_dir():
				path_elements = file.filename[len(search_folder):].split("/")
				if self.debuglevel > 0:
					print("zip path_elements:", path_elements)

				# Is this a file which is a direct child of the searched folder?
				# If it is a file of a supported type, included it in the list of images.
				if len(path_elements) == 1:
					filename = path_elements[0]
					if mimetype := extmap.get(os.path.splitext(filename)[1]):
						self.files.append(self.PlaylistItem(
							id = file.filename,
							title = filename,
							filename = filename,
							mimetype = mimetype,
							file_size = file.file_size,
							thumbnail = (self.zip_reader, file.filename, mimetype),
							))
						if self.debuglevel > 0:
							print(self.files[-1])
							print()

				# Is this a file which is a grandchild of the search folder?
				# If we have not yet included this folder in the list of subfolders
				# of search_folder and this file is a supported image, include the
				# folder using this image as the thumbnail.
				elif len(path_elements) == 2:
					dirname, filename = path_elements
					if not dirname in folders_included:
						if mimetype := extmap.get(os.path.splitext(filename)[1]):
							self.folders.append(self.PlaylistItem(
								id = search_folder + dirname,
								title = dirname,
								filename = dirname,
								thumbnail = (self.zip_reader, file.filename, mimetype),
								))
							if self.debuglevel > 0:
								print(self.folders[-1])
								print()
						folders_included.add(dirname)

	# Load image list from a playlist shared from JW Library (.jwlplaylist).
	def _load_jwlplaylist(self, manifest):
		self.folder_name = manifest.get("name")

		# The playlist is in a Sqlite DB. We extract it to a temporary file and open it.
		dbfile = self.zip_reader.read("userData.db")

		tempfile_name = conn = None
		try:
			tempfile, tempfile_name = mkstemp(suffix=".db")
			with os.fdopen(tempfile, "wb") as fh:
				fh.write(dbfile)
			conn = sqlite3.connect(tempfile_name)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()

			# Run a query to loop through the files in the playlist
			for row in cur.execute("""
					select Label, FilePath, MimeType, DocumentId as MepsDocumentId, KeySymbol, Track, IssueTagNumber, ThumbnailFilePath
						from PlaylistItem
						left join PlaylistItemIndependentMediaMap using(PlaylistItemId)
						left join IndependentMedia using(IndependentMediaId)
						left join PlaylistItemLocationMap using(PlaylistItemId)
						left join Location using(LocationId);
					"""):
				row = dict(row)
				if self.debuglevel > 0:
					print("jwlplaylist item:", json.dumps(row, indent=4, ensure_ascii=False))

				# Image file inside the playlist zip
				#
				# Label -- whatever user set in the app (default is the original filename)
				# FilePath -- random ID basename + ".jpg"
				# MimeType -- "image/jpeg"
				# MepsDocumentId -- None
				# KeySymbol -- None
				# Track -- None
				# IssueTagNumber -- None
				#
				# We don't bother testing that the file is actually present since playlists
				# have no mechanism for linking to external image files.
				if row["MimeType"] and row["MimeType"].startswith("image/"):
					id = row["FilePath"]
					filename = None
					mimetype = row["MimeType"]
					file_size = None

				# Video file inside the playlist zip
				# (Users can add their own images and videos when creating a playlist in the app.)
				#
				# Make sure the file is actually in the zip since there is no guarantee that in future
				# playlists could not have MimeType and FilePath set for external videos.
				elif row["MimeType"] and row["MimeType"].startswith("video/") \
						and row["FilePath"] \
						and (info := self._find_embedded_file(self.zip_reader, row)):
					id = row["FilePath"]
					filename = row["FilePath"]
					mimetype = row["MimeType"]
					file_size = info.file_size

				# Videos which must be downloaded from JW.ORG one way or another
				# FilePath -- None
				# MimeType -- None
				# Video identified either by MepsDocumentId or KeySymbol and Track
				# IssueTagNumber -- 0
				elif gfile := self._find_neighbor_file(row):
					id = "gdrive:" + gfile.id
					filename = gfile.filename
					mimetype = gfile.mimetype
					file_size = gfile.size
				else:
					id = self._make_video_id(row)
					filename = None
					mimetype = "video/mp4"
					file_size = None

				self.files.append(self.PlaylistItem(
					id = id,
					title = row["Label"],
					filename = filename,
					mimetype = mimetype,
					file_size = file_size,
					# Both images and videos have thumbnails in the zip
					thumbnail = (self.zip_reader, row["ThumbnailFilePath"], "image/jpeg"),
					))
				if self.debuglevel > 0:
					print(self.files[-1])
					print()

		finally:
			if conn is not None:
				conn.close()
			if tempfile_name is not None:
				os.unlink(tempfile_name)

	# Load image list from a JWPUB file such as the Public Talk Media Playlist (S-34mp_U.jwpub)
	def _load_jwpub_playlist(self, manifest):
		publication = manifest["publication"]

		# For some reason JWPUB files are double zipped
		contents = self.zip_reader.open_zipfile("contents")

		# The playlist is in a Sqlite DB. We extract it to a temporary file and open it.
		dbfile = contents.read(publication["fileName"])
		tempfile_name = conn = None
		try:
			tempfile, tempfile_name = mkstemp(suffix=".db")
			with os.fdopen(tempfile, "wb") as fh:
				fh.write(dbfile)
			conn = sqlite3.connect(tempfile_name)
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()

			# Root level: Table of Contents (lists talks)
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
					if self.debuglevel > 0:
						print("jwpub document item:", json.dumps(row, indent=4, ensure_ascii=False))
					self.folders.append(self.PlaylistItem(
						id = row["DocumentId"],
						title = row["Title"],
						filename = row["Title"],	# FIXME
						thumbnail = (contents, row["ThumbnailFilePath"], row["ThumbnailMimeType"]),
						))
					if self.debuglevel > 0:
						print(self.folders[-1])

			# Numberically-named subdirectories each contains the media for a talk
			else:
				docid = int(self.path[0])
				cur.execute("select Title from Document where DocumentId = ?", (docid,))
				self.folder_name = cur.fetchone()[0]

				# Run a query to loop through the files in the selected talk's playlist
				for row in cur.execute("""
						select DocumentId,
								Multimedia.MultimediaId,
								Multimedia.Label, Multimedia.FilePath, Multimedia.MimeType,
								Multimedia.KeySymbol, Multimedia.Track, Multimedia.IssueTagNumber, MultiMedia.MepsDocumentId,
								Multimedia2.MultimediaId as ThumbnailMultimediaId, Multimedia2.FilePath as ThumbnailFilePath, Multimedia2.MimeType as ThumbnailMimeType
							from Document
							inner join DocumentMultimedia using(DocumentId)
							inner join Multimedia using(MultimediaId)
							left outer join Multimedia as Multimedia2 on Multimedia.LinkMultimediaId=Multimedia2.MultimediaId
							where Document.DocumentId = ?
						""", (docid,)):
					row = dict(row)
					if self.debuglevel > 0:
						print("jwpub playlist item:", json.dumps(row, indent=4, ensure_ascii=False))
					assert row["DocumentId"] == docid

					# .jwpub files specify the mimetype for both images and video
					assert row["MimeType"]

					# Image files are packed inside the playlist zip file itself
					# Label -- empty string in talk playlists
					# FilePath -- the original file name as used on JW.ORG
					# MimeType -- "image/jpeg"
					# KeySymbol, Track, MepsDocumentId, and IssueTagNumber are all None or 0
					# ThumbnailFilePath and ThumbnailMimeType are also None
					# (In this respect .jwpub files are different from .jwlplaylist files.)
					if row["MimeType"].startswith("image/"):
						id = "contents:"+row["FilePath"]
						filename = row["FilePath"]
						file_size = None
						if not row["ThumbnailFilePath"]:
							row["ThumbnailFilePath"] = row["FilePath"]
							row["ThumbnailMimeType"] = row["MimeType"]

					# Videos must be downloaded from JW.ORG
					#
					# Label -- empty string
					# FilePath -- filename of the 720i version as downloaded from JW.ORG (or empty string)
					#             (File is NOT included in the zip)
					# MimeType -- "video/mp4"
					# Video identified either by MepsDocumentId or KeySymbol and Track
					# IssueTagNumber -- 0
					# ThumbnailFilePath -- filename in JW.ORG style (file IS included in zip)
					# ThumbnailMimeType -- "image/jpeg"
					#
					# First we look in Google Drive to see if the user has downloaded it.
					# If we don't find it, we generate a sharing link and hope for the best.
					elif gfile := self._find_neighbor_file(row):
						id = "gdrive:" + gfile.id
						filename = gfile.filename
						file_size = gfile.file_size
					else:
						id = self._make_video_id(row)
						filename = row["FilePath"]
						if not filename:
							if row["MepsDocumentId"] is not None:
								filename = "docid-%s-%d" % (row["MepsDocumentId"], row["Track"])
							else:
								filename = "pub-%s-%d" % (row["KeySymbol"], row["Track"])
						file_size = None

					self.files.append(self.PlaylistItem(
						id = id,
						title = row["Label"] or filename,
						filename = filename,
						mimetype = row["MimeType"],
						file_size = file_size,
						thumbnail = (contents, row["ThumbnailFilePath"], row["ThumbnailMimeType"]),
						))
					if self.debuglevel > 0:
						print(self.files[-1])
						print()
		finally:
			if conn is not None:
				conn.close()
			if tempfile_name is not None:
				os.unlink(tempfile_name)

	def _find_embedded_file(self, zip_reader, row):
		try:
			return zip_reader.getinfo(row["FilePath"])
		except KeyError:
			return None

	# Given a row from the playlist's Sqlite DB, return a JW.ORG sharing URL.
	# For use with .jwlplaylist and .jwpub playlists
	def _make_video_id(self, row):

		assert row["Track"] is not None and row["Track"] >= 1

		# A video on a standalone player page identified by the MEPS ID of that page
		if row["MepsDocumentId"]:
			return "https://www.jw.org/finder?" + urlencode({
				"lank": f"docid-{row['MepsDocumentId']}_{row['Track']}_VIDEO",
				})

		# A video as a media item of a songbook or talk outline
		if row["KeySymbol"]:

			# Check our list of videos from JW Broadcasting
			lank = f"pub-{row['KeySymbol']}_{row['Track']}_VIDEO"
			#if Videos.query.filter_by(lank=lank).first():
			return "https://www.jw.org/finder?" + urlencode({"lank": lank})

			# Make a sharing URL and hope for the best
			query = {
				"pub": row["KeySymbol"],
				"track": row["Track"],
				}
			if row["IssueTagNumber"]:
				query["issue"] = str(row["IssueTagNumber"])
			return "https://www.jw.org/finder?" + urlencode(query)

		raise AssertionError("Can't make URL: %s" % row)

	# Find a file in the Gdrive folder which contains the current zipped playlist
	def _find_neighbor_file(self, row):
		if self.parent_reader is None:
			self.parent_reader = self.client_class(self.path_to[:-1], [])
		pattern = f"{row['KeySymbol']}_*_{row['Track']:02}_r*P.mp4"
		if self.debuglevel > 0:
			print("media file search pattern:", pattern)
		for gfile in self.parent_reader.list_image_files():
			if self.debuglevel > 1:
				print("  candidate file:", gfile.filename)
			if fnmatch(gfile.filename, pattern):
				if self.debuglevel > 0:
					print(f" Match: {gfile.filename}")
				return gfile
		else:
			if self.debuglevel > 0:
				print(" No match")
		return None
