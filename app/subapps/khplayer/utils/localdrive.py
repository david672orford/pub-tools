import os
import io
import base64
from PIL import Image

from ....utils.babel import gettext as _
from .mimetypes import extmap
from .httpfile import LocalZip

class LocalDriveClient:
	def __init__(self, path_to:list, path_within:list, thumbnails=False, debug=False):
		assert len(path_to) > 0
		assert len(path_within) == 0
		self.debug = debug

		if len(path_to) == 1:
			self.folder_name = _("Local Speaker's Slides Folder")
		else:
			self.folder_name = path_to[-1]

		self.path = os.path.abspath(os.path.join(*path_to))
		assert self.path == path_to[0] or self.path.startswith(path_to[0] + "/")

		self.folders = []
		self.image_files = []
		for file in os.scandir(self.path):
			basename, ext = os.path.splitext(file.name)
			if file.is_dir():
				self.folders.append(self.LocalFile(file, None))
			elif ext in {".zip", ".jwlplaylist", ".jwpub"}:
				self.folders.append(self.LocalFile(file, "application/zip"))
			elif (mimetype := extmap.get(ext)):
				self.image_files.append(self.LocalFile(file, mimetype, thumbnail=True))

	class LocalFile:
		def __init__(self, file, mimetype, thumbnail:bool=False):
			self.id = file.name
			self.title = file.name
			self.filename = file.name
			self.mimetype = mimetype
			self.file_size = file.stat().st_size
			self.thumbnail_data = None

			if thumbnail and self.mimetype.startswith("image/"):
				image = Image.open(file.path)
				image.thumbnail((184, 105))
				save_to = io.BytesIO()
				image.save(save_to, format="jpeg", quality=85)
				self.thumbnail_data = save_to.getvalue()

		@property
		def thumbnail_url(self):
			if self.thumbnail_data is None:
				return None
			return "data:{mimetype};base64,{data}".format(
				mimetype = "image/jpeg",
				data = base64.b64encode(self.thumbnail_data).decode("utf-8"),
				)

	def list_folders(self):
		"""Get the list of objects representing the subfolders"""
		return self.folders

	def list_image_files(self):
		"""Get the list of objects representing the images files"""
		return self.image_files

	def make_uuid(self, file):
		return None

	def download_thumbnail(self, file, save_as):
		if file.thumbnail_data is None:
			return None
		save_as = os.path.splitext(save_as)[0] + ".jpg"
		with open(save_as + ".tmp", "wb") as fh:
			fh.write(file.thumbnail_data)
		os.rename(save_as + ".tmp", save_as)
		return save_as

	def download_file(self, file, save_as, callback=None):
		return os.path.join(self.path, file.id)
