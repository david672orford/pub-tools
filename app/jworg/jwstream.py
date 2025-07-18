# encoding=utf-8

import sys, os, re, json, logging
import requests
from urllib.parse import urlparse, unquote
from time import time
from datetime import datetime, date, timezone
from .wtcodes import meps_language_code_to_name, meps_country_code_to_name

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

def parse_jwstream_share_url(url):
	url_obj = urlparse(url)
	m = re.match(r"^/ts/([0-9a-zA-Z]{10})$", url_obj.path)
	if m is None:
		m = re.match(r"^/(\d{4}-\d{4}-\d{4}-\d{4})$", url_obj.path)
	if url_obj.netloc == "stream.jw.org" and m is not None:
		return m.group(1)
	return None

# The JW Stream API gives certain timestamps as decimal strings of the
# number of milliseconds since the start of the Unix epoch.
def convert_datetime(milliseconds_since_epoch, fudge=0):
	timestamp = datetime.fromtimestamp(int(milliseconds_since_epoch) / 1000 + fudge, timezone.utc)
	return timestamp

program_types = {
	"midweekMeeting": "Midweek Meeting",
	"weekendMeeting": "Weekend Meeting",
	}

class StreamEvent:
	"""A recording of an event (a meeting or talk)"""

	def __init__(self, requester, event):
		self.requester = requester
		self.event = event
		self.id = event["key"]
		extra = json.loads(event["additionalFields"])
		program_type = event["categoryProgramType"]
		if program_type == "publicTalk":
			self.datetime = convert_datetime(extra["date"])
			self.title = "%s %s" % (extra["talkNumber"], extra["themeAndFullName"])
		else:
			week_of = (
				convert_datetime(extra["startDateRange"], fudge=(3 * 3600)).date(),
				convert_datetime(extra["endDateRange"], fudge=(3 * 3600)).date(),
				)
			self.datetime = week_of[0]
			#self.title = "%s thru %s %s" % (week_of[0], week_of[1], program_types.get(program_type, program_type))
			self.title = program_types.get(program_type, program_type)
		self.duration = int(event["duration"] / 1000)
		self.language = meps_language_code_to_name(event["languageCode"])
		self.country = meps_country_code_to_name(event["countryCode"])
		self._preview_url = None
		self._download_url = None
		self._chapters = None

	@property
	def chapters(self):
		if self._chapters is None:
			response = self.requester.session.get(
				"https://stream.jw.org/api/v1/program/getByGuidForHome/vod/{guid}".format(
					guid = self.event["downloadUrls"][0]["guid"],
					),
				timeout = self.requester.request_timeout,
				)
			if response.status_code != 200:
				raise StreamError("getByGuidForHome failed: %d %s" % (response.status_code, response.text))
			info2 = response.json()
			#print("info2:", json.dumps(info2, indent=2))
			self._chapters = sorted(info2["chapters"], key=lambda item: int(item["editedStartTime"]))
		return self._chapters

	def get_preview_url(self):
		if self._preview_url is None:
			self._preview_url = self.get_video_url(self.requester.config["preview_resolution"])
		return self._preview_url

	def get_download_url(self):
		if self._download_url is None:
			self._download_url = self.get_video_url(self.requester.config["download_resolution"])
		return self._download_url

	def get_video_url(self, resolution):
		for download_url in self.event["downloadUrls"]:
			m = re.match(r"^(\d+)", download_url["quality"])
			if int(m.group(1)) == resolution:
				break
		else:
			logger.error("JW Stream event %s not found in resolution %s", id, resolution)
			return None

		# Ask site to generate an access token and add it to the download URL
		response = self.requester.session.put(
			"https://stream.jw.org/api/v1/libraryBranch/program/presignURL",
			json = download_url,
			timeout = self.requester.request_timeout,
			)
		if response.status_code != 201:
			raise StreamError("presignURL failed: %d %s" % (response.status_code, response.text))
		response = response.json()
		logger.debug("presignURL response: %s", response)
		return response["presignedUrl"]

class StreamRequester:
	"""Client for JW Stream"""

	user_agent = "Mozilla/5.0"
	request_timeout = 30

	def __init__(self, url, config, debug=False):
		self.debug = debug
		self.channel_key = None
		self.name = None
		self.language = None
		self.country = None
		self.status = None
		self.video_info = []
		self.events = []

		self.config = dict(
			preview_resolution = 234,
			download_resolution = 720,
			)
		self.config.update(config)

		for usage in ("preview", "download"):
			res = self.config.get(usage + "_resolution")
			if not res in (234, 360, 540, 720):
				raise StreamConfigError("Invalid %s_resolution: %s" % (usage, res))

		self.token = parse_jwstream_share_url(url)
		if self.token is None:
			raise StreamConfigError("Not a JW Stream share URL: %s" % url)

		self.session = requests.Session()
		self.session.headers.update({
			"User-Agent": self.user_agent,
			"Accept": "application/json",
			})

		# Use the sharing URL to log in and get the session cookies
		response = self.session.post(
			"https://stream.jw.org/api/v1/auth/login/share",
			json = { "token": self.token },
			timeout = self.request_timeout,
			)
		if response.status_code == 401:
			self.status = "expired"		# sharing URL is too old
			return
		if response.status_code != 201:
			raise StreamError("auth/login/share failed: %s %s" % (response.status_code, response.text))

		# Get the access tokens
		response = self.session.get(
			"https://stream.jw.org/api/v1/auth/whoami",
			headers = {
				"xsrf-token-stream": self.session.cookies.get_dict()["xsrf-token-stream"],
				},
			timeout = self.request_timeout,
			)
		if response.status_code != 201:
			raise StreamError("auth/whoami failed: %s %s" % (response.status_code, response.text))

		whoami = response.json()
		self.session.headers["xsrf-token-stream"] = whoami["xsrfToken"]
		self.status = whoami["status"]

		# Get info about this JW Stream sharing link
		response = self.session.get(
			"https://stream.jw.org/api/v1/libraryBranch/home/subCategory/theocraticProgram",
			timeout = self.request_timeout,
			)
		if response.status_code != 200:
			raise StreamError("subCategory/theocraticProgram failed: %s %s" % (response.status_code, response.text))
		data = response.json()
		logger.debug("theocraticProgram: %s" % json.dumps(data, indent=2))
		try:
			info = data[0]["specialties"][0]
		except (IndexError, KeyError):
			logger.error("No content: %s" % url)
			return
		self.channel_key = info["key"]
		self.name = info["name"]
		self.language = meps_language_code_to_name(info["languageCode"])
		self.country = meps_country_code_to_name(info["countryCode"])

		self.reload()

	# Ask for the list of current videos
	def reload(self):
		if self.channel_key is None:
			return

		# Use the channel key to get a list of the events
		response = self.session.get("https://stream.jw.org/api/v1/libraryBranch/home/vodProgram/specialty/%s" % self.channel_key,
			timeout = self.request_timeout,
			)
		if response.status_code != 200:
			raise StreamError("%d %s" % (response.status_code, response.text))
		self.video_info = response.json()

		if self.debug:
			with open("debug-videos.json", "w") as fh:
				json.dump(self.video_info, fh, indent=2, ensure_ascii=False)

		self.events = [StreamEvent(self, event) for event in self.video_info]

	# Get a list of the events
	def list_events(self):
		return self.events

	# Get what we need to play one of the events
	def get_event(self, id):
		for event in self.events:
			if event.id == id:
				return event
		logger.error("JW Stream event %s not found", id)
		return None

class StreamRequesterContainer(dict):
	"""Create a client for each JW Stream sharing URL supplied"""
	def __init__(self, config):
		for url in config.get("urls","").split():
			requestor = StreamRequester(url, config)
			self[requestor.token] = requestor

if __name__ == "__main__":
	import sys
	requester = StreamRequester(sys.argv[1], {}, debug=True)
	for event in requester.list_events():
		print("Event: %s: %s" % (event.id, event.title))

	if len(sys.argv) > 2:
		event = requester.get_event(sys.argv[2])
		if event is None:
			print("Not found")
		else:
			print("Program name:", event.title)
			print("Video URL:", event.get_download_url())
			print("Chapters:", event.chapters)
