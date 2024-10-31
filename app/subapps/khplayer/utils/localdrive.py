

class LocalFile:
	def __init__(self, file, thumbnail_url):
		self.id = file[0]
		self.title = file[2]
		self.filename = file[2]
		self.mimetype = file[3]
		self.file_size = file[13]
		self.thumbnail_url = thumbnail_url

class LocalDriveClient:
	def __init__(self, id, thumbnails=False, cachedir="cache", debug=False):
		self.folder_id = id
		self.cachedir = cachedir
		self.debug = debug

	def list_folders(self):
		"""Get the list of objects representing the subfolders"""
		return self.folders
		
	def list_image_files(self):
		"""Get the list of objects representing the images files"""
		return self.image_files

	def make_uuid(self, file):
		return file.id

	def download_thumbnail(self, file, save_as):
		pass

	def download_file(self, file, save_as, callback=None):
		pass

