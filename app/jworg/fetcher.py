import os
from urllib.request import Request, HTTPHandler, HTTPSHandler, HTTPError, HTTPErrorProcessor, build_opener
from urllib.parse import urlparse, parse_qsl, urlencode, unquote
from gzip import GzipFile
import lxml.html
import json
import re
from time import sleep, time
import logging

from ..utils.babel import gettext as _
from .codes import iso_language_code_to_meps

logger = logging.getLogger(__name__)

class FetcherError(Exception):
	pass

class NoRedirects(HTTPErrorProcessor):
	def http_response(self, request, response):
		if response.code in (301, 302, 303, 307):
			return response
		else:
			return super.http_response(request, response)

class GzipResponseWrapper:
	def __init__(self, response):
		self.response = response
		self.gzip = GzipFile(fileobj=response)
	def read(self, size=None):
		return self.gzip.read(size)
	def geturl(self):
		return self.response.geturl()
	@property
	def headers(self):
		return self.response.headers

class Fetcher:
	user_agent = "Mozilla/5.0"

	request_timeout = 30

	# Minimum time between requests (in seconds)
	min_request_interval = 2.5

	# This API endpoint is used used to find the media files (MP3, MP4) which go
	# with a printed publication or the publication itself in downloadable
	# electronic form (such as PDF or Epub).
	#
	# Query string parameters:
	# * pub -- the publication abbreviation
	# * output -- set to "json"
	# * fileformat -- a comma-separated list of file extensions such as "m4v,mp4,3gp,mp3"
	# * alllangs -- generally "0"
	# * track -- song number
	# * langwritten -- language code ("U" for Russian)
	# * txtCMSLang -- language code (not clear how different from langwritten)
	#
	# Alternatively:
	# * docid -- the MEPS document ID
	# * output=json
	# * fileformat=mp4,mp3
	# * alllangs=1
	# * track=1
	# * langwritten=
	# * txtCMSLang=
	#
	# Note that this API does not provide a thumbnail image.
	#
	pub_media_url = 'https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS'

	# Used for listing videos from JW Broadcasting by category
	# Query string parameters:
	# detailed=1 -- list subcategories and videos in this category
	# clientType=www -- Unknown
	mediator_categories_url = 'https://data.jw-api.org/mediator/v1/categories/{language}/{category}?detailed=1&clientType=www'

	# Used for getting the download link for a video from JW Broadcasting when
	# we know the language we want and the video's Language Agnostic Natural Key (lank)
	mediator_items_url = 'https://b.jw-cdn.org/apis/mediator/v1/media-items/{language}/{video}'

	# Page in Watchtower Online Library which gives the study articles for a given week
	# It is necessary to parse the HTML to get the links to the articles and their docids.
	week_url = "https://wol.jw.org/en/wol/meetings/r1/lp-e/{year}/{week}"

	def __init__(self, language="ru", cachedir="cache", debuglevel=0):
		self.meps_language = iso_language_code_to_meps(language)
		self.cachedir = cachedir
		self.last_request_time = 0
		http_handler = HTTPHandler(debuglevel=debuglevel)
		https_handler = HTTPSHandler(debuglevel=debuglevel)
		self.opener = build_opener(http_handler, https_handler)
		self.no_redirects_opener = build_opener(NoRedirects, http_handler, https_handler)

	# Send an HTTP GET request
	def get(self, url, query=None, accept="text/html, */*", follow_redirects=True):
		left_to_wait = (self.min_request_interval - (time() - self.last_request_time))
		if left_to_wait > 0:
			sleep(left_to_wait)
		if query:
			url = url + '?' + urlencode(query)
		logger.debug("Fetching %s...", unquote(url))
		request = Request(
			url,
			headers={
				"Accept": accept,
				"Accept-Encoding": "gzip",
				"Accept-Language": "en-US",
				"User-Agent": self.user_agent,
				}
			)
		if follow_redirects:
			response = self.opener.open(request, timeout=self.request_timeout)
		else:
			response = self.no_redirects_opener.open(request, timeout=self.request_timeout)
		if response.headers.get("Content-Encoding") == "gzip":
			response = GzipResponseWrapper(response)
		self.last_request_time = time()
		return response

	# Send an HTTP GET request and parse the result as HTML.
	def get_html(self, url, query=None):
		response = self.get(url, query=query)
		return lxml.html.parse(response).getroot()

	# Send an HTTP GET request and parse the result as JSON
	def get_json(self, url, query=None):
		response = self.get(url, query, accept="application/json")
		return json.load(response)

	# Pretty print a parsed HTML element and its children. We need this because
	# in a browser JavaScript code transforms the page a bit after it is loaded,
	# so we can't completely trust what we seen in the browser's debugger.
	@staticmethod
	def dump_html(el, filename=None):
		Fetcher._indent(el)
		text = lxml.html.tostring(el, encoding="UNICODE")
		if filename:
			with open(filename, "w") as fh:
				fh.write(text)
		else:
			logger.debug("=======================================================\n%s", text)

	@staticmethod
	def dump_json(data):
		text = json.dumps(data, indent=4, ensure_ascii=False)
		logger.debug("=======================================================\n%s", text)

	# Alter the whitespace in the element tree to indent the tabs
	# https://web.archive.org/web/20200130163816/http://effbot.org/zone/element-lib.htm#prettyprint
	@staticmethod
	def _indent(elem, level=0):
		i = "\n" + level*"  "
		if len(elem):
			if not elem.text or not elem.text.strip():
				elem.text = i + "  "
			if not elem.tail or not elem.tail.strip():
				elem.tail = i
			for elem in elem:
				Fetcher._indent(elem, level+1)
			if not elem.tail or not elem.tail.strip():
				elem.tail = i
		else:
			if level and (not elem.tail or not elem.tail.strip()):
				elem.tail = i

	def get_title(self, url):
		html = self.get_html(url)
		title = html.xpath("./head/title")
		if len(title) > 0:
			return title[0].text
		else:
			return "No Title"

	# Download a video or picture, store it in the cache directory, and return its path.
	def download_media(self, url: str, callback=None):
		cachefile = os.path.join(self.cachedir, os.path.basename(urlparse(url).path))
		if not os.path.exists(cachefile):
			response = self.get(url)
			total_expected = int(response.headers.get("Content-Length"))
			with open(cachefile + ".tmp", "wb") as fh:
				total_recv = 0
				last_callback = 0
				while True:
					chunk = response.read(0x10000)	# 64k
					if not chunk:
						break
					fh.write(chunk)
					total_recv += len(chunk)
					logger.debug("%d byte chunk, %s of %s bytes received", len(chunk), total_recv, total_expected)
					if callback:
						now = time()
						if (now - last_callback) >= 0.5 or total_recv == total_expected:
							callback("{total_recv} of {total_expected}", total_recv=total_recv, total_expected=total_expected)
							last_callback = now
			os.rename(cachefile + ".tmp", cachefile)
			logger.debug("Media file downloaded, %d bytes received", total_recv)
		return os.path.abspath(cachefile)

	# Get the URL of the video file for a song identified by number
	def get_song_video_url(self, song_number: int, resolution=None):
		media = self.get_json(self.pub_media_url, query = {
			'output': 'json',
			'pub': 'sjjm',
			'fileformat': 'm4v,mp4,3gp,mp3',
			'alllangs': '0',
			'track': str(song_number),
			'langwritten': self.meps_language,
			'txtCMSLang': self.meps_language,
			})
		for variant in media['files'][self.meps_language]['MP4']:
			if variant["label"] == resolution:
				return variant['file']['url']
		raise AssertionError("No match for resolution %s" % resolution)

	# Given a link to a video from an article, extract the publication ID
	# and language and go directly to the mediator endpoint to get the
	# metadata bypassing the player page.
	#
	# url -- sharing URL for video
	# resolution -- 
	# language -- optional language override, ISO code
	def get_video_metadata(self, url, resolution=None, language=None):
		query = dict(parse_qsl(urlparse(url).query))

		# Video is specified by its Language Agnostic Natural Key (LANK)
    	# https://www.jw.org/finder?lank=pub-jwbcov_201505_11_VIDEO&wtlocale=U
		# https://www.jw.org/open?lank=pub-mwbv_202103_2_VIDEO&wtlocale=U
		if "lank" in query:

			if language is not None:
				wtlocale = iso_language_code_to_meps(language)
			else:
				wtlocale = query["wtlocale"]

			media = self.get_json(self.mediator_items_url.format(
				language = wtlocale,
				video = query["lank"],
				), query = { "clientType": "www" })
			if len(media["media"]) < 1:
				raise FetcherError("Video metadata has empty media section: %s %s" % (url, media))
			media = media["media"][0]

			# If the caller has specified a video resolution, find a suitable file.
			mp4_url = None
			if resolution is not None:
				for variant in media["files"]:
					if variant.get("mimetype") == "video/mp4" and variant.get("label") == resolution:
						mp4_url = variant["progressiveDownloadURL"]
						break

			try:
				thumbnail_url = media['images']['wss']['sm']		# 16:9 aspect ratio, occassionally missing
			except KeyError:
				thumbnail_url = media['images']['lss']['lg']		# 2:1 aspect ratio

			subtitles_url = None
			for variant in media["files"]:
				if "subtitles" in variant:
					subtitles_url = variant["subtitles"]["url"]

			return {
				"title": media["title"],
				"url": mp4_url,
				"thumbnail_url": thumbnail_url,
				"subtitles_url": subtitles_url,
				}

		# Video is specified by its MEPS Document ID
		if "docid" in query:

			docid = int(query["docid"])
			if 1102016801 <= docid <= 1102016951:
				params = {
					"pub": "sjjm",
					"track": str(docid - 1102016800),
					}
			else:
				params = {
					"docid": query["docid"],
					"track": "1",
					}

			params.update({
				"output": "json",
				"fileformat": "mp4,mp3",
				"alllangs": "0",		# 1 observed, use 0 because we don't need all the languages
				"langwritten": query["wtlocale"],
				"txtCMSLang": query["wtlocale"],
				})

			media = self.get_json(self.pub_media_url, query = params)
			mp4 = media["files"][query["wtlocale"]]["MP4"]

			# If the caller has specified a video resolution, look for a matching file.
			mp4_url = None
			if resolution is not None:
				for variant in mp4:
					if variant.get("label") == resolution:
						mp4_url = variant["file"]["url"]
						break

			# The pub-media API does not provide a thumbnail image. Get an image from the player page.
			player_page = self.get_html(url)
			poster_div = player_page.find(".//div[@class='jsVideoPoster mid%s']" % query["docid"])
			thumbnail_url = poster_div.attrib["data-src"] if poster_div is not None else None

			return {
				"title": mp4[0]["title"],
				"url": mp4_url,
				"subtitles_url": mp4[0]["subtitles"]["url"] if "subtitles" in mp4[0] else None,
				"thumbnail_url": thumbnail_url,
				}

		return None

	# Find the EPUB download URL of a periodical
	# FIXME: is this really just for periodicals? Note that issue_code is optional
	def get_epub_url(self, pub_code, issue_code=None):
		logger.debug("get_epub_url(%s, %s)", pub_code, issue_code)
		query = {
			'output': 'json',
			'pub': pub_code,
			'fileformat': 'EPUB',
			'alllangs': '0',
			'langwritten': self.meps_language,
			'txtCMSLang': self.meps_language,
			}
		if issue_code is not None:
			query['issue'] = issue_code
		try:
			media = self.get_json(self.pub_media_url, query=query)
		except HTTPError as e:
			logger.error("Failed to fetch EPUB url for %s %s: %s", pub_code, issue_code, str(e))
			return None
		return media['files'][self.meps_language]['EPUB'][0]['file']['url']

