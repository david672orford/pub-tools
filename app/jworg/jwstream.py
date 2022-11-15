# encoding=utf-8

import sys, os
import requests
import json
from urllib.parse import urlparse, unquote
from time import time
import logging

logger = logging.getLogger(__name__)

#import http.client as http_client
#http_client.HTTPConnection.debuglevel = 1

class StreamRequester:
	user_agent = "Mozilla/5.0"

	def __init__(self, config, cachefile=None, debug=False):
		self.config = dict(
			url = None,
			preview_resolution = 234,
			download_resolution = 720,
			)
		self.config.update(config)
		assert "url" in self.config, "JW Stream url not set"
		for usage in ("preview", "download"):
			res = self.config.get(usage + "_resolution")
			assert res in (234, 360, 540, 720), "Invalid %s_resolution: %s" % (usage, res)

		self.config = config
		self.cachefile = cachefile
		self.debug = debug

		self.session = None
		self.video_info = None

		# Extract the token from an invitation URL. It is the last segment of the path.
		self.token = unquote(urlparse(self.config['url']).path.split("/")[-1])

	def connect(self):
		self.session = requests.Session()
		self.session.headers.update({
			'User-Agent': self.user_agent
			})

		# If we have a cache, we can load the cookies and the list of videos
		# and don't have to go through the whole process of retrieving it all again.
		if self.cachefile is not None and os.path.exists(self.cachefile):
			with open(self.cachefile,"r") as fh:
				try:
					cache = json.load(fh)
					for cookie in cache['cookies']:
						self.session.cookies.set(**cookie)
					self.video_info = cache['video_info']
					print("Satisified from cache")
					return
				except json.JSONDecodeError:
					pass

		# Load the invitation page in order to get the cookies.
		# One of these cookies contains a token which we must use when
		# making AJAX requests.
		page_response = self.session.get(self.config['url'])
		assert page_response.status_code == 200

		# Headers to simulate an AJAX request from a browser
		ajax_headers = {
			"Content-Type": "application/json;charset=UTF-8",
			"Referer": "https://fle.stream.jw.org/video/ru-ukr",
			"Accept": "application/json, text/plain, */*",
			"X-Requested-With": "XMLHttpRequest",
			"X-XSRF-Token": page_response.cookies['XSRF-TOKEN'],
			}

		# This returns a list of the available languages. On reloads it
		# returns only the language indicated in the response to getinfo.
		response = self.session.post("https://fle.stream.jw.org/language/getlanguages", headers=ajax_headers)
		assert response.status_code == 200, response.text
		getlanguages = response.json()
		if self.debug:
			with open("debug-getlanguages.json", "w") as fh:
				json.dump(getlanguages, fh, indent=2, ensure_ascii=False)

		# Use the token from the invitation URL to log in
		response = self.session.post("https://fle.stream.jw.org/token/check",
			headers = ajax_headers,
			json = { 'token': self.token }
			)
		assert response.status_code == 200, response.text
		assert response.json()[0]			# response should be [True]

		# Get a JSON blob of information about this sharing link.
		response = self.session.post("https://fle.stream.jw.org/member/getinfo", headers=ajax_headers)
		assert response.status_code == 200, response.text
		getinfo = response.json()
		if self.debug:
			with open("debug-getinfo.json", "w") as fh:
				json.dump(getinfo, fh, indent=2, ensure_ascii=False)

		# Find the primary language of the sharing link in the least downloaded earlier.
		language = getinfo['data']['language']
		for language_blob in getlanguages['languages']:
			if language_blob['locale'] == language:
				self.language_blob = language_blob
				break
		else:
			raise AssertionError("Failed to find language: %s" % language)

		language_blob.update({
			# No idea whether these are actually important.
			# "русский"
			"translatedName": self.language_blob['vernacular'],
			# "русский (Україна)",
			"translatedNameWithCountry": "{vernacular} ({country_description})".format(**language_blob),
			# "русский (Україна) (ru)"
			"translatedNameWithSymbol":  "{vernacular} ({country_description}) ({symbol})".format(**language_blob),
			# "русский (Україна) (ru-ukr)"
			"translatedNameWithLocale":  "{vernacular} ({country_description}) ({locale})".format(**language_blob),
			})

		# Ask for the list of current videos
		# Though we supply the language and country information, this actually gets
		# all of the programs shared through this sharing link irrespective of language.
		response = self.session.post("https://fle.stream.jw.org/event/languageVideos",
			headers = ajax_headers,
			data = json.dumps(
				dict(language = language_blob),
				ensure_ascii = False,
				separators = (',', ':')
				).encode("utf-8")
			)
		assert response.status_code == 200, response.text
		self.video_info = response.json()

		if self.debug:
			with open("debug-languageVideos.json", "w") as fh:
				json.dump(self.video_info, fh, indent=2, ensure_ascii=False)

		# Write the cookies and the list of videos to a cache file
		if self.cachefile is not None:
			cookies = []
			for cookie in self.session.cookies:
				cookies.append(dict(
					name = cookie.name,
					value = cookie.value,
					domain = cookie.domain,
					path = cookie.path,
					expires = cookie.expires,
					))
			print("cookies:", cookies)
			with open(self.cachefile, "w") as fh:
				json.dump(dict(
					cookies = cookies,
					video_info = self.video_info,
					timestamp = int(time()),
					), fh, indent=2, ensure_ascii=False)

	def get_events(self):
		for event in self.video_info:
			yield (event['data']['id'], event['title'])

	def get_event(self, id, preview=True):
		for event in self.video_info:
			if event['data']['id'] == id:
				break
		else:
			return None

		print(json.dumps(event['vod_files'], indent=2))
		resolution = self.config["preview_resolution" if preview else "download_resolution"]
		for vod_file in event['vod_files']:
			if vod_file['height'] == resolution:
				url = vod_file['url']
				break
		else:
			return None

		# Try to fetch the video file. The result will be a redirect to a CDN.
		result = self.session.get(url, allow_redirects=False)
		assert result.status_code == 302
		return (event['title'], result.headers['Location'], event['chapters'])

if __name__ == "__main__":
	import sys
	requester = StreamRequester(sys.argv[1], cachefile="jwstream-cache.json", debug=False)
	requester.connect()
	for id, name in requester.get_events():
		print("Event: %d: %s" % (id, name))

	video_url, chapters = requester.get_event(int(sys.argv[2]))
	print("Video URL:", video_url)
	print("Chapters:", chapters)

