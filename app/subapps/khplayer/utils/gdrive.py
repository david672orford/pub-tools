from urllib.request import Request, HTTPHandler, HTTPSHandler, build_opener
from urllib.parse import urlparse, parse_qsl, urlencode, unquote
import lxml.html
import os, json, re

class GDriveClient:
	user_agent = "Mozilla/5.0"
	request_timeout = 30

	def __init__(self, config, cachedir="cache", debuglevel=0):
		self.config = config
		self.cachedir = cachedir
		self.debuglevel = debuglevel
		self.debug = (debuglevel > 0)
		http_handler = HTTPHandler(debuglevel=debuglevel)
		https_handler = HTTPSHandler(debuglevel=debuglevel)
		self.opener = build_opener(http_handler, https_handler)
		self.root = self.get_html(self.config["url"])

	def get(self, url, query=None):
		if query:
			url = url + '?' + urlencode(query)
		request = Request(
			url,
			headers={
				"Accept": "text/html, */*",
				#"Accept-Encoding": "gzip",
				"Accept-Language": "en-US",
				"User-Agent": self.user_agent,
				}
			)
		response = self.opener.open(request, timeout=self.request_timeout)
		return response

	def get_html(self, url, query=None):
		response = self.get(url, query=query)
		return lxml.html.parse(response).getroot()

	# Return a list of objects representing the images files at the top
	# level of this Google Drive folder.
	def list_files(self):
		if self.debug:
			text = lxml.html.tostring(self.root, encoding="UNICODE")
			with open("gdrive.html", "w") as fh:
				fh.write(text)

		# Parsing approach from:
		# https://github.com/wkentaro/gdown/
		data = None
		for script in self.root.iterfind(".//script"):
			if script.text is not None and "_DRIVE_ivd" in script.text:
				js_iter = re.compile(r"'((?:[^'\\]|\\.)*)'").finditer(script.text)
				item = next(js_iter).group(1)
				assert item == "_DRIVE_ivd", item
				item = next(js_iter).group(1)
				decoded = item.encode("utf-8").decode("unicode_escape")
				data = json.loads(decoded)

				if self.debug:
					with open("gdrive.json", "w") as fh:
						json.dump(data, fh, indent=4)

				break

		assert data is not None	

		class GFile:
			def __init__(self, file):
				self.id = file[0]
				self.filename = file[2]
				self.mimetype = file[3]
			@property
			def thumbnail_url(self):
				return "https://lh3.google.com/u/0/d/%s=w400-h380-p-k-rw-v1-nu-iv1" % self.id
			@property
			def download_url(self):
				return "https://drive.google.com/uc?export=download&id=%s" % self.id

		for file in data[0]:
			if file[3].startswith("image/"):
				yield GFile(file)

	def download(self, file):
		cachefile = os.path.join(self.cachedir, "user-" + file.filename)
		response = self.get(file.download_url)
		with open(cachefile, "wb") as fh:
			while True:
				chunk = response.read(0x10000) # 64k
				if not chunk:
					break
				fh.write(chunk)
		return cachefile

