# encoding=utf-8

import sys
import requests
import json
from urllib.parse import urlparse, unquote
import logging

logger = logging.getLogger(__name__)

#import http.client as http_client
#http_client.HTTPConnection.debuglevel = 1

class StreamRequester:
	user_agent = "Mozilla/5.0"

	def __init__(self, url):
		self.url = url
		self.session = None
		self.ajax_headers = None
		self.video_info = None

	def connect(self):
		self.session = requests.Session()
		self.session.headers.update({
			'User-Agent': self.user_agent
			})

		# Extract the token from an invitation URL
		token = unquote(urlparse(self.url).path.split("/")[-1])

		# Load the invitation page in order to get the cookies
		page_response = self.session.get(self.url)
		assert page_response.status_code == 200

		# Headers to simulate an AJAX request from a browser
		self.ajax_headers = {
			"Content-Type": "application/json;charset=UTF-8",
			"Referer": "https://fle.stream.jw.org/video/ru-ukr",
			"Accept": "application/json, text/plain, */*",
			"X-Requested-With": "XMLHttpRequest",
			"X-XSRF-Token": page_response.cookies['XSRF-TOKEN'],
			}

		# Use the token from the invitation URL to log in
		response = self.session.post("https://fle.stream.jw.org/token/check",
			headers = self.ajax_headers,
			json = { 'token': token }
			)
		assert response.status_code == 200
		assert response.json()[0]

	def get_videos(self):
		# Ask for the list of current videos
		response = self.session.post("https://fle.stream.jw.org/event/languageVideos",
			headers = self.ajax_headers,
			data = json.dumps({
				"language": {
					"id_language": "749",
					"symbol": "ru",
					"locale": "ru-ukr",
					"code_tv": None,
					"name": "Russian",
					"vernacular": "русский",
					"spellings": None,
					"direction": "ltr",
					"is_sign": "0",
					"has_content": "1",
					"id_branch_channel": "2578",
					"has_translation": "1",
					"date_format": "Y-m-d",
					"country_description": "Україна",
					"version": None,
					"translatedName": "русский",
					"translatedNameWithCountry": "русский (Україна)",
					"translatedNameWithSymbol": "русский (Україна) (ru)",
					"translatedNameWithLocale": "русский (Україна) (ru-ukr)"
					}
				}, ensure_ascii=False, separators=(',', ':')).encode("utf-8")
			)
		assert response.status_code == 200
		self.video_info = response.json()

	# Save the list of videos to a file for study
	def dump(self):
		with open("video_info.json", "w") as fh:
			json.dump(self.video_info, fh, indent=2, ensure_ascii=False)

	def find_event(self, name_prefix):
		for event in self.video_info:
			if event['title'].startswith(name_prefix):
				return event
		return None

	def get_event(self, name_prefix, resolution):
		event = self.find_event(name_prefix)
		assert event
		chapters = list(map(lambda chapter: chapter['time'], event['chapters']))
		print(json.dumps(event['vod_files'], indent=2))
		for vod_file in event['vod_files']:
			if vod_file['height'] == resolution:
				url = vod_file['url']
				break
		else:
			return None

		# Try to fetch the video file. The result will be a redirect to a CDN.
		result = self.session.get(url, allow_redirects=False)
		assert result.status_code == 302
		return (result.headers['Location'], chapters)

if __name__ == "__main__":
	import sys
	requester = StreamRequester(sys.argv[1])
	requester.connect()
	requester.get_videos()
	video_url, chapters = requester.get_event(sys.argv[2], int(sys.argv[3] if len(sys.argv) >= 4 else 234))
	print("Video URL:", video_url)
	print("Chapters:", chapters)

