#
# Simple client for downloading files from Google Drive. Does not log in. To
# use it you create a sharing URL (to share with "anyone with the link") and
# extract the ID from it.
#
# Common Google Drive URL patterns:
#
# When you get when you share a folder:
#  https://drive.google.com/drive/folders/{id}?usp=sharing
# What the browser retrieves when you download a file:
#  https://drive.google.com/uc?export=download&id={id}
# Reportedly you can get image thumbnails like this:
#  https://drive.google.com/thumbnail?id={id}&sz=w{width}-h{height}
# This is what we actually observed for thumbnails:
#  https://lh3.googleusercontent.com/u/0/d/{id}=w400-h380-p-k-rw-v1-nu-iv1
# Reportedly you can embed a folder view in an <iframe> using one of these URLs:
#  https://drive.google.com/embeddedfolderview?id={id}#list
#  https://drive.google.com/embeddedfolderview?id={id}#grid
# 
import os, json, re, base64, codecs
import requests
import lxml.etree
import lxml.html

class GFile:
	def __init__(self, file, thumbnail_url):
		self.id = file[0]
		self.filename = file[2]
		self.mimetype = file[3]
		self.thumbnail_url = thumbnail_url

class IterAsFile:
	def __init__(self, iterator):
		self.iterator = iterator
	def read(self, size=None):
		chunk = next(self.iterator, None)
		if chunk is None:
			return ""
		return chunk

class GDriveClient:
	def __init__(self, id, thumbnails=False, cachedir="cache", debug=False):
		self.cachedir = cachedir
		self.debug = debug

		url = "https://drive.google.com/drive/folders/{id}?usp=sharing".format(id=id)
		self.session = requests.Session()
		response = self.session.get(url, stream=True)
		root = lxml.etree.parse(IterAsFile(response.iter_content()), parser=lxml.etree.HTMLParser(encoding=response.encoding)).getroot()

		if self.debug:
			text = lxml.html.tostring(root, encoding="UNICODE")
			with open("gdrive.html", "w") as fh:
				fh.write(text)

		self.folder_name = root.find(".//title").text

		# Find the JSON object which contains the list of files.
		#
		# Extraction approach from:
		#   https://github.com/wkentaro/gdown/
		# Correct decoding from:
		#   https://stackoverflow.com/questions/990169/how-do-convert-unicode-escape-sequences-to-unicode-characters-in-a-python-string
		#
		data = None
		for script in root.iterfind(".//script"):
			if script.text is not None and "_DRIVE_ivd" in script.text:
				# Find single-quoted strings
				js_iter = re.compile(r"'((?:[^'\\]|\\.)*)'").finditer(script.text)
				item = next(js_iter).group(1)
				assert item == "_DRIVE_ivd", item
				item = next(js_iter).group(1)
				decoded = codecs.escape_decode(item)[0].decode("utf-8")
				data = json.loads(decoded)
				if self.debug:
					with open("gdrive.json", "w") as fh:
						json.dump(data, fh, indent=4, ensure_ascii=False)
				break
		assert data is not None, "_DRIVE_ivd not found"

		# * If the folder is empty, data[0] will be null
		# * If the folder is not empty, data[0] will contain a list of files
		# * Each file entry:
		#   * 0 -- GDrive ID of this file
		#   * 1 -- One-element array containing what looks like another Gdrive ID
		#   * 2 -- The filename
		#   * 3 -- The MIME type
		#   * The rest of the array is mainly nulls and numbers like 0 and 1 with a few
		#   * things that look like timestamps and a URL to view the file thrown in.
		self.folders = []
		self.image_files = []
		if data[0] is not None:
			for file in data[0]:
				if self.debug:
					print("gdrive file:", file[0], file[2], file[3])
				if file[3] in ("application/vnd.google-apps.folder", "application/zip", "application/x-zip"):
					self.folders.append(GFile(file, None))
				elif file[3].startswith("image/"):
					if thumbnails:
						response = self.session.get("https://lh3.googleusercontent.com/u/0/d/{id}=w400-h380-p-k-rw-v1-nu-iv1".format(id=file[0]))
						thumbnail_url = "data:{mimetype};base64,{data}".format(
							mimetype = response.headers.get("Content-Type","").split(";")[0],
							data = base64.b64encode(response.content).decode("utf-8"),
							)
					else:
						thumbnail_url = None
					self.image_files.append(GFile(file, thumbnail_url))
				elif file[3].startswith("video/"):
					self.image_files.append(GFile(file, None))
				else:		# other files
					pass

	# Get the list of objects representing the subfolders.
	def list_folders(self):
		return self.folders
		
	# Get the list of objects representing the images files.
	def list_image_files(self):
		return self.image_files

	def get_file(self, file):
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		url = "https://drive.google.com/uc?export=download&id={id}".format(id=file.id)
		response = self.session.get(url)
		with open(cachefile, "wb") as fh:
			fh.write(response.content)
		return cachefile

