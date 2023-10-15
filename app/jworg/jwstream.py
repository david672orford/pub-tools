# encoding=utf-8

import sys, os, re, json, logging
import requests
from urllib.parse import urlparse, unquote
from time import time
from datetime import datetime, date, timezone
from .codes import language_code_to_name, country_code_to_name

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

# The JW Stream API gives certain timestamps as decimal strings of the
# number of milliseconds since the start of the Unix epoch.
def convert_datetime(milliseconds_since_epoch, fudge=0):
	timestamp = datetime.fromtimestamp(int(milliseconds_since_epoch) / 1000 + fudge, timezone.utc)
	return timestamp

program_types = {
	"midweekMeeting": "Midweek Meeting",
	"weekendMeeting": "Weekend Meeting",
	}

# A recording of an event
class StreamEvent:
	def __init__(self, event, download_url=None, chapters=None):
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
		self.language = language_code_to_name(event["languageCode"])
		self.country = country_code_to_name(event["countryCode"])
		self.download_url = download_url
		self.chapters = chapters

class StreamRequester:
	user_agent = "Mozilla/5.0"
	request_timeout = 30

	def __init__(self, url, config, debug=False):
		self.token = unquote(urlparse(url).path.split("/")[-1])

		self.config = dict(
			preview_resolution = 234,
			download_resolution = 720,
			)
		self.config.update(config)

		for usage in ("preview", "download"):
			res = self.config.get(usage + "_resolution")
			if not res in (234, 360, 540, 720):
				raise StreamConfigError("Invalid %s_resolution: %s" % (usage, res))

		self.debug = debug

		self.session = requests.Session()
		self.session.headers.update({
			'User-Agent': self.user_agent,
			"Accept": "application/json",
			})

		# Use the sharing URL to log in and get the session cookies
		response = self.session.post(
			"https://stream.jw.org/api/v1/auth/login/share",
			json = { "token": self.token },
			timeout = self.request_timeout,
			)
		if response.status_code != 201:
			raise StreamError("auth/login/share failed: %s %s" % (response.status_code, response.text))

		# Get the tokens
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
		self.expires = convert_datetime(whoami["expiresOn"])
		self.status = whoami["status"]

		# Get info about this link
		response = self.session.get(
			"https://stream.jw.org/api/v1/libraryBranch/home/subCategory/theocraticProgram",
			timeout = self.request_timeout,
			)
		if response.status_code != 200:
			raise StreamError("subCategory/theocraticProgram failed: %s %s" % (response.status_code, response.text))
		info = response.json()[0]["specialties"][0]
		self.channel_key = info["key"]
		self.name = info["name"]
		self.language = language_code_to_name(info["languageCode"])
		self.country = country_code_to_name(info["countryCode"])

		self.reload()

	# Ask for the list of current videos
	def reload(self):

		# Use the channel key to get a list of the programs
		response = self.session.get("https://stream.jw.org/api/v1/libraryBranch/home/vodProgram/specialty/%s" % self.channel_key,
			timeout = self.request_timeout,
			)
		if response.status_code != 200:
			raise StreamError("%d %s" % (response.status_code, response.text))
		self.video_info = response.json()

		if self.debug:
			with open("debug-videos.json", "w") as fh:
				json.dump(self.video_info, fh, indent=2, ensure_ascii=False)

	# Get a list of the events
	def list_events(self):
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
			logger.error("JW Stream event %s not found in resolution %s", id, resolution)
			return None

		# Ask site to generate to create an access token and add it to the download URL
		response = self.session.put(
			"https://stream.jw.org/api/v1/libraryBranch/program/presignURL",
			json = download_url,
			timeout = self.request_timeout,
			)
		if response.status_code != 201:
			raise StreamError("presignURL failed: %d %s" % (response.status_code, response.text))
		download_url = response.json()

		# Get the chapters
		response = self.session.get(
			"https://stream.jw.org/api/v1/program/getByGuidForHome/vod/%s" % download_url["guid"],
			timeout = self.request_timeout,
			)
		if response.status_code != 200:
			raise StreamError("getByGuidForHome failed: %d %s" % (response.status_code, response.text))
		info2 = response.json()
		chapters = sorted(info2["chapters"], key=lambda item: int(item["editedStartTime"]))

		return StreamEvent(event, download_url["presignedUrl"], chapters)

class StreamRequesterContainer(dict):
	def __init__(self, config):
		for url in config["url"].split():
			requestor = StreamRequester(url, config)
			self[requestor.token] = requestor

if __name__ == "__main__":
	import sys
	requester = StreamRequester(sys.argv[1], {}, debug=True)
	for event in requester.list_events():
		print("Event: %s: %s" % (event.id, event.title))

	if len(sys.argv) > 2:
		event = requester.get_event(sys.argv[2])
		print("Program name:", event.title)
		print("Video URL:", event.download_url)
		print("Chapters:", event.chapters)

