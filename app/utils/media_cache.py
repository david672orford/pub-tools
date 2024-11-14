from datetime import datetime
import os.path
import re

from flask import current_app

from ..jworg.filenames import is_jworg_filename

# Give information about a file, produce a cache path to which to save it.
# Choices:
# * If it looks like a JW.ORG filename, use it as-is
# * If a UUID (based on Gdrive) is supplied, use that, with or without the filename
# * If all else fails, produce a unique name
class MakeMediaCachefileName:
	def __init__(self):
		self.datestamp = datetime.now().strftime("%Y%m%d%H%M%S")
		self.serial = 1

	def __call__(self, filename, mimetype, uuid=None):
		print(f"make_media_cachefile_name({repr(filename)}, {repr(mimetype)}, {repr(uuid)})")

		# If this looks like a JW.ORG filename, use it as the cache key.
		if filename is not None and is_jworg_filename(filename):
			pass

		else:
			# Get the extension, either from the filename, or from the mimetype
			if filename is not None and (m := re.search(r"\.([a-zA-Z0-9]+)$", filename)):
				ext = m.group(1) if m else ""
			else:
				ext = {
					"image/jpeg": "jpg",
					"video/mp4": "mp4",
					}[mimetype]

			# If we have a UUID for this file, use that as the cache key
			if uuid is not None:
				filename = f"user-{uuid}.{ext}"

			# Don't have a stable cache key. Save to name in form user-YYYYMMDDHHMMSS-X.ext.
			else:
				filename = f"user-{self.datestamp}-{self.serial}.{ext}"
				self.serial += 1

		cachefile = os.path.abspath(os.path.join(
			current_app.config["MEDIA_CACHEDIR"],
			filename,
			))
		print("cachefile:", cachefile)
		return cachefile

make_media_cachefile_name = MakeMediaCachefileName()

