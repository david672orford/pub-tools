from datetime import datetime
import os.path
import re

from flask import current_app

from ..jworg.filenames import is_jworg_filename

datestamp = datetime.now().strftime("%Y%m%d%H%M%S")
serial = 1

# If a media file was not downloaded directly from JW.ORG, we use this function
# to create its cache file name. If its name fits the pattern of files from
# JW.ORG, we use it as is. Otherwise we generate a unique name.
#
# TODO: 
# * consider generating unique names for Gdrive files
def make_media_cachefile_name(filename):
	global serial, datestamp
	filename = os.path.basename(filename)
	if not is_jworg_filename(filename):
		# Save to file with name in format user-YYYYMMDDHHMMSS-X.ext
		m = re.search(r"(\.[a-zA-Z0-9]+)$", filename)
		ext = m.group(1) if m else ""
		filename = "user-%s-%d%s" % (datestamp, serial, ext)
		serial += 1
	return os.path.abspath(os.path.join(
		current_app.config["MEDIA_CACHEDIR"],
		filename,
		))

