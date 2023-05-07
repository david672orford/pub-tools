# encoding=utf-8

import sys, os, re, json, logging
import requests
from urllib.parse import urlparse, unquote
from time import time
from datetime import datetime, date, timezone

logger = logging.getLogger(__name__)

#import http.client as http_client
#http_client.HTTPConnection.debuglevel = 1

# New JW Stream introduced 1 May 2023
#
# * A different link for each event channel in the form https://stream.jw.org/ts/*token*
# * Links are good for 30 days
# * GET https://stream.jw.org/api/v1/auth/whoami
#   Returns 401 Unauthorized if user is not logged in
# * POST to https://stream.jw.org/api/v1/auth/login/share as JSON: {token: "*token*"}
#   returns session_stream and xsrf-token-stream cookies
# * GET https://stream.jw.org/api/v1/auth/whoami
#   returns JSON which repeats back all three tokens
# * GET https://stream.jw.org/api/v1/program/live
#   Returns []
# * POST https://stream.jw.org/api/v1/libraryBranch/home/whatsNew
#   Returns {whatsNewPrograms: [...], whatsNewSpecialties: [...]}
# * GET https://stream.jw.org/api/v1/libraryBranch/home/category
#   Returns [{categoryType: "theocraticProgram"}]
# * GET https://stream.jw.org/api/v1/libraryBranch/home/subCategory/theocraticProgram
#   returns {categoryType: "congregationMeeting", specialties: [key: "*UUID*", ...]
# * GET https://stream.jw.org/api/v1/libraryBranch/home/vodProgram/specialty/*UUID*
#   returns [{},...]
#   * downloadUrls (MP4)
#   * playUrl (M3U8)
# * PUT https://stream.jw.org/api/v1/libraryBranch/program/presignURL
#   Body is an entry from downloadUrls
#   Response is the same except download URL is repeated back with token in presignedUrl
# * GET https://stream.jw.org/api/v1/program/getByGuidForHome/vod/*GUID*
#   Returns the same info as the "specialty" call above but for a single video
#   and with the addition of a "chapters" item

class StreamError(Exception):
	pass

class StreamConfigError(StreamError):
	pass

# A recording of an event
class StreamEvent:
	def __init__(self, event, download_url=None, chapters=None):
		self.id = event["key"]
		extra = json.loads(event["additionalFields"])
		self.week_of = (
			self.convert_datetime(extra["startDateRange"], fudge=(3 * 3600)).date(),
			self.convert_datetime(extra["endDateRange"], fudge=(3 * 3600)).date(),
			)
		self.title = "%s from %s to %s" % (
			event["categoryProgramType"], self.week_of[0], self.week_of[1]
			)
		self.datetime = self.convert_datetime(event["publishedDate"])
		self.language = event["languageCode"]
		self.language_country = event["countryCode"]
		self.download_url = download_url
		self.chapters = chapters

	def convert_datetime(self, milliseconds_since_epoch, fudge=0):
		timestamp = datetime.fromtimestamp(int(milliseconds_since_epoch) / 1000 + fudge, timezone.utc)
		return timestamp	

class StreamRequester:
	user_agent = "Mozilla/5.0"

	def __init__(self, config, cachefile=None, debug=False):
		self.config = dict(
			url = None,
			preview_resolution = 234,
			download_resolution = 720,
			)
		self.config.update(config)
		if not "url" in self.config:
			raise StreamConfigError("JW Stream url not set")
		for usage in ("preview", "download"):
			res = self.config.get(usage + "_resolution")
			if not res in (234, 360, 540, 720):
				raise StreamConfigError("Invalid %s_resolution: %s" % (usage, res))

		self.cachefile = cachefile
		self.debug = debug

		self.session = None
		self.tokens = None
		self.video_info = []

	def connect_hook(self):
		if self.session is None or ((int(self.tokens["expiresOn"]) / 1000) - time()) < 300:
			self.connect()

	def connect(self):
		self.session = requests.Session()
		self.session.headers.update({
			'User-Agent': self.user_agent,
			"Accept": "application/json",
			})

		# If we have a cache, we can load the cookies and the list of videos
		# and don't have to go through the whole process of retrieving it all again.
		if self.cachefile is not None and os.path.exists(self.cachefile):
			with open(self.cachefile,"r") as fh:
				try:
					cache = json.load(fh)
					logger.debug("JW Stream cache time left: %s", ((int(cache["tokens"]["expiresOn"]) / 1000) - time()))
					if ((int(cache["tokens"]["expiresOn"]) / 1000) - time()) >= 300:
						logger.debug("Loading JW Stream cache...")
						for cookie in cache['cookies']:
							self.session.cookies.set(**cookie)
						self.tokens = cache['tokens']
						self.session.headers["xsrf-token-stream"] = self.tokens["xsrfToken"]
						self.video_info = cache['video_info']
						logger.debug("JW Stream session loaded from cache")
						return
				except json.JSONDecodeError:		# bad cache file
					logger.warning("Bad JW Stream cache file: JSON decode error")
				except KeyError as e:				# obsolete cache file
					logger.warning("Bad JW Stream cache file: %s not found" % e)

		# Use the sharing URL to log in 
		response = self.session.post("https://stream.jw.org/api/v1/auth/login/share",
			json = {
				"token": unquote(urlparse(self.config['url']).path.split("/")[-1])
				}
			)
		if response.status_code != 201:
			raise StreamError("share failed: %s %s" % (response.status_code, response.text))

		# Get the tokens
		response = self.session.get("https://stream.jw.org/api/v1/auth/whoami",
			headers = {
				"xsrf-token-stream": self.session.cookies.get_dict()["xsrf-token-stream"],
				}
			)
		if response.status_code != 201:
			raise StreamError("whoami failed: %s %s" % (response.status_code, response.text))
		self.tokens = response.json()
		self.session.headers["xsrf-token-stream"] = self.tokens["xsrfToken"]

		self.update_videos()
		self.write_cache()

	# Ask for the list of current videos
	# Though we supply the language and country information, this actually gets
	# all of the programs shared through this sharing link irrespective of language.
	def update_videos(self):
		response = self.session.get("https://stream.jw.org/api/v1/libraryBranch/home/subCategory/theocraticProgram")
		if response.status_code != 200:
			raise StreamError("subCategory failed: %s %s" % (response.status_code, response.text))
		channel_key = response.json()[0]["specialties"][0]["key"]

		response = self.session.get("https://stream.jw.org/api/v1/libraryBranch/home/vodProgram/specialty/%s" % channel_key)
		if response.status_code != 200:
			raise StreamError("%d %s" % (response.status_code, response.text))
		self.video_info = response.json()

		if self.debug:
			with open("debug-videos.json", "w") as fh:
				json.dump(self.video_info, fh, indent=2, ensure_ascii=False)

	# Write the cookies and the list of videos to a cache file
	def write_cache(self):
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
			with open(self.cachefile, "w") as fh:
				json.dump(dict(
					cookies = cookies,
					tokens = self.tokens,
					video_info = self.video_info,
					), fh, indent=2, ensure_ascii=False)

	# Refresh the list of videos
	def reload(self):
		self.connect_hook()
		self.update_videos()
		self.write_cache()

	# Get a list of the events
	def get_events(self):
		self.connect_hook()
		for event in self.video_info:
			yield StreamEvent(event)

	# Get what we need to play one of the events
	def get_event(self, id, preview=True):
		for event in self.video_info:
			if event["key"] == id:
				break
		else:
			logger.error("JW Stream event %s not found", id)
			return None

		resolution = self.config["preview_resolution" if preview else "download_resolution"]
		for download_url in event['downloadUrls']:
			m = re.match(r"^(\d+)", download_url['quality'])
			if int(m.group(1)) == resolution:
				break
		else:
			logger.error("JW Stream event %s not found in resolution", id, resolution)
			return None

		self.connect_hook()

		response = self.session.put("https://stream.jw.org/api/v1/libraryBranch/program/presignURL",
			json = download_url,
			)
		if response.status_code != 201:
			raise StreamError("presignURL failed: %d %s" % (response.status_code, response.text))
		download_url = response.json()

		response = self.session.get("https://stream.jw.org/api/v1/program/getByGuidForHome/vod/%s" % download_url["guid"])
		if response.status_code != 200:
			raise StreamError("getByGuidForHome failed: %d %s" % (response.status_code, response.text))
		info2 = response.json()

		return StreamEvent(event, download_url["presignedUrl"], info2['chapters'])

if __name__ == "__main__":
	import sys
	requester = StreamRequester({"url": sys.argv[1]}, cachefile="jwstream-cache.json", debug=False)
	requester.connect()
	for event in requester.get_events():
		print("Event: %s: %s" % (event.id, event.title))

	name, video_url, chapters = requester.get_event(sys.argv[2])
	print("Program name:", name)
	print("Video URL:", video_url)
	print("Chapters:", chapters)

