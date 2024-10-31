import os
import io
import base64
from PIL import Image

from .mimetypes import extmap
from .httpfile import LocalZip

class LocalFile:
	def __init__(self, file, mimetype, thumbnail_url=None):
		self.id = file.name
		self.title = file.name
		self.filename = file.name
		self.mimetype = mimetype
		self.file_size = file.stat().st_size
		self.thumbnail_url = thumbnail_url

class LocalDriveClient:
	def __init__(self, path_to:list, path_within:list, thumbnails=False, cachedir="cache", debug=False):
		assert len(path_to) > 0
		assert len(path_within) == 0
		self.folder_name = path_to[-1]
		self.debug = debug

		self.path = os.path.abspath(os.path.join(*path_to))
		assert self.path == path_to[0] or self.path.startswith(path_to[0] + "/")

		self.folders = []
		self.image_files = []
		for file in os.scandir(self.path):
			basename, ext = os.path.splitext(file.name)
			if file.is_dir():
				self.folders.append(LocalFile(file, None))
			elif ext in {".zip", ".jwlplaylist", ".jwpub"}:
				self.folders.append(LocalFile(file, "application/zip"))
			elif (mimetype := extmap.get(ext)):
				thumbnail_url = self.make_thumbnail(self.path, file.name, mimetype)
				self.image_files.append(LocalFile(file, mimetype, thumbnail_url=thumbnail_url))

	def make_thumbnail(self, folder_path, filename, mimetype):
		if not mimetype.startswith("image/"):
			return None
		path = os.path.join(folder_path, filename)
		image = Image.open(path)
		image.thumbnail((184, 105))
		save_to = io.BytesIO()
		image.save(save_to, format="jpeg", quality=85)
		encoded_data = base64.b64encode(save_to.getvalue()).decode("utf-8")
		return f"data:image/jpeg;base64,{encoded_data}"

	def list_folders(self):
		"""Get the list of objects representing the subfolders"""
		return self.folders
		
	def list_image_files(self):
		"""Get the list of objects representing the images files"""
		return self.image_files

	def make_uuid(self, file):
		return None

	def download_thumbnail(self, file, save_as):
		return None

	def download_file(self, file, save_as, callback=None):
		return os.path.join(self.path, file.id)

