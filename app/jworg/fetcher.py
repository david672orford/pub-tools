import os, json, re
from urllib.request import Request, HTTPHandler, HTTPSHandler, HTTPError, HTTPErrorProcessor, build_opener
from urllib.parse import urlparse, parse_qsl, urlencode, unquote
from gzip import GzipFile
from time import sleep, time
from functools import cache
import logging

import lxml.html

from ..utils.babel import gettext as _
from .wtcodes import iso_language_code_to_meps

logger = logging.getLogger(__name__)

class FetcherError(Exception):
	pass

class FetcherNoMediaError(FetcherError):
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
	# Note that this API does not provide a thumbnail image (even though
	# the response seems to have a space for one).
	#
	pub_media_url = "https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS"

	# The Mediator API endpoint is Used for listing videos from JW Broadcasting by category
	# Query string parameters:
	# detailed=1 -- list subcategories and videos in this category
	# clientType=www -- Unknown purpose
	#mediator_categories_url = "https://data.jw-api.org/mediator/v1/categories/{meps_language}/{category}?detailed=1&clientType=www"
	mediator_categories_url = "https://b.jw-cdn.org/apis/mediator/v1/categories/{meps_language}/{category}?detailed=1&clientType=www"

	# Used for getting the download link for a video from JW Broadcasting when
	# we know the language we want and the video's Language Agnostic Natural Key (lank)
	mediator_items_url = "https://b.jw-cdn.org/apis/mediator/v1/media-items/{meps_language}/{video}"

	# Page in Watchtower Online Library which gives the study articles for a given week
	# It is necessary to parse the HTML to get the links to the articles and their docids.
	week_url = "https://wol.jw.org/en/wol/meetings/r1/lp-e/{year}/{week}"

	def __init__(self, language=None, cachedir=None, debuglevel=0):
		if language is None:
			raise FetcherError("Language must be set")
		self.language = language
		self.meps_language = iso_language_code_to_meps(language)
		self.cachedir = cachedir
		self.last_request_time = 0
		http_handler = HTTPHandler(debuglevel=debuglevel)
		https_handler = HTTPSHandler(debuglevel=debuglevel)
		self.opener = build_opener(http_handler, https_handler)
		self.no_redirects_opener = build_opener(NoRedirects, http_handler, https_handler)

	# Send an HTTP HEAD request
	def head(self, url):
		return self.request(url, method="HEAD")

	# Send an HTTP GET request
	def get(self, url, **kwargs):
		return self.request(url, method="GET", **kwargs)

	# Send an HTTP request
	def request(self, url, query=None, accept="text/html, */*", follow_redirects=True, method="GET"):
		left_to_wait = (self.min_request_interval - (time() - self.last_request_time))
		if left_to_wait > 0:
			sleep(left_to_wait)
		if query:
			url = url + '?' + urlencode(query)
		logger.debug("Fetching %s...", unquote(url))
		request = Request(
			url,
			headers = {
				"Accept": accept,
				"Accept-Encoding": "gzip",
				"Accept-Language": "en-US",
				"User-Agent": self.user_agent,
				},
			method = method,
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
		response = self.get(url, query=query, accept="application/json")
		return json.load(response)

	# Download a video or picture from a URL, store it in the cache
	# directory, and return its path.
	def download_media(self, url:str, cachefile:str=None, callback=None):
		if cachefile is None:
			if self.cachedir is None:
				raise FetcherError("Cachedir is not set")
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

	#======================================================================
	# For debugging
	#======================================================================

	# Pretty print a parsed HTML element and its children. We need this because
	# in a browser JavaScript code transforms the page a bit after it is loaded,
	# so we can't completely trust what we seen in the browser's debugger.
	def dump_html(self, el, filename=None):
		self.indent_html(el)
		text = lxml.html.tostring(el, encoding="UNICODE")
		if filename:
			with open(filename, "w") as fh:
				fh.write(text)
		else:
			logger.debug("=======================================================\n%s", text)

	# Alter the whitespace in the element tree to indent the tabs
	# https://web.archive.org/web/20200130163816/http://effbot.org/zone/element-lib.htm#prettyprint
	def indent_html(self, elem, level=0):
		i = "\n" + level*"  "
		if elem.tag == "span":
			pass
		elif len(elem):
			if not elem.text or not elem.text.strip():
				elem.text = i + "  "
			if not elem.tail or not elem.tail.strip():
				elem.tail = i
			for elem in elem:
				self.indent_html(elem, level+1)
			if not elem.tail or not elem.tail.strip():
				elem.tail = i
		else:
			if level and (not elem.tail or not elem.tail.strip()):
				elem.tail = i

	@staticmethod
	def dump_json(data):
		text = json.dumps(data, indent=4, ensure_ascii=False)
		logger.debug("=======================================================\n%s", text)

	#======================================================================
	# The Pub Media API is used to find:
	# 1) Alternative versions of a publication
	# 2) Supplements such as recorded music for a songbook
	#======================================================================

	# Get the URL of a media file which accompanies a publication
	def get_pub_media(self, query:dict):
		logger.debug(f"get_pub_media(query=%s)", query)
		final_query = {
			"output": "json",
			"fileformat": query.get("fileformat", "m4v,mp4,3gp,mp3"),
			"alllangs": "0",		# 1 observed, use 0 because we don't need all the languages
			"langwritten": self.meps_language,
			"txtCMSLang": self.meps_language,
			}
		if query.get("pub") is not None:
			final_query["pub"] = query["pub"]
		if query.get("issue") is not None:
			final_query["issue"] = query["issue"]
		if query.get("track") is not None:
			final_query["track"] = str(query["track"])
		if query.get("docid") is not None:
			final_query["docid"] = query["docid"]
		media = self.get_json(self.pub_media_url, query = final_query)
		return media

	# Find the EPUB download URL of a publication
	def get_epub_url(self, pub:str, issue:str=None):
		try:
			media = self.get_pub_media({
				"pub": pub,
				"issue": issue,
				"fileformat": "EPUB",
				})
		except HTTPError as e:
			logger.error("Failed to fetch EPUB url for %s %s: %s", pub, issue, str(e))
			return None
		return media["files"][self.meps_language]["EPUB"][0]["file"]["url"]

	#======================================================================
	# Given the URL of a video on JW.ORG, get its metadata and
	# optionally, the URL of the MP4 file
	#======================================================================

	# Get the metadata for a video
	# * url -- sharing URL for video
	# * resolution (optional) -- "240p", "360p", "480p", or "720p"
	# * language -- optional language override, ISO code
	# Return None if this does not appear to be a link to a video on JW.ORG.
	@cache
	def get_video_metadata(self, url:str, resolution:int=None, language:str=None):
		assert isinstance(url, str)

		query = self.parse_video_url(url)

		if language is not None:
			meps_language = iso_language_code_to_meps(language)
		elif "wtlocale" in query:
			meps_language = query["wtlocale"]
		else:
			meps_language = self.meps_language

		# Video is specified by its Language Agnostic Natural Key (LANK)
		# Examples:
		#  https://www.jw.org/finder?lank=pub-jwbcov_201505_11_VIDEO&wtlocale=U
		#  https://www.jw.org/open?lank=pub-mwbv_202103_2_VIDEO&wtlocale=U
		if "lank" in query:

			media = self.get_json(self.mediator_items_url.format(
				meps_language = meps_language,
				video = query["lank"],
				), query = { "clientType": "www" })
			if len(media["media"]) < 1:
				raise FetcherNoMediaError("Video not yet available: %s" % url)
			media = media["media"][0]

			# If the caller has specified a video resolution, find a suitable file.
			mp4_url = None
			if resolution is not None:
				for variant in media["files"]:
					if variant.get("mimetype") == "video/mp4" and variant.get("label") == resolution:
						mp4_url = variant["progressiveDownloadURL"]
						break

			try:
				thumbnail_url = media["images"]["wss"]["sm"]		# 16:9 aspect ratio, occassionally missing
			except KeyError:
				thumbnail_url = media["images"]["lss"]["lg"]		# 2:1 aspect ratio

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

		if "pub" in query or "docid" in query:

			# Video specified by publication and track
			if "pub" in query:
				params = {
					"pub": query["pub"],
					"track": query["track"],
					}

			# Video is specified by its MEPS Document ID
			else:
				params = {
					"docid": query["docid"],
					}
				assert "track" not in query

			media = self.get_pub_media(params)
			self.dump_json(media)

			mp4 = media["files"][meps_language].get("MP4")
			if mp4 is None:
				logger.info("No video files")
				return None

			# If the caller has specified a video resolution, look for a matching file.
			mp4_url = None
			if resolution is not None:
				for variant in mp4:
					if variant.get("label") == resolution:
						mp4_url = variant["file"]["url"]
						break

			# The pub-media API does not provide a thumbnail image. Get an image from the player page.
			#player_page = self.get_html(url)
			#poster_div = player_page.find(".//div[@class='jsVideoPoster mid%s']" % query["docid"])
			#thumbnail_url = poster_div.attrib["data-src"] if poster_div is not None else None
			thumbnail_url = None

			return {
				"title": mp4[0]["title"],
				"url": mp4_url,
				"subtitles_url": mp4[0]["subtitles"]["url"] if "subtitles" in mp4[0] else None,
				"thumbnail_url": thumbnail_url,
				}

		logger.info("Not a share URL: %s", unquote(url))
		return None

	# We have split out the URL parsing so we an use return.
	#
	# The March 2018 MWB is the first to link to the sample presentation videos:
	#  https://www.jw.org/finder?wtlocale=U&docid=202018083&srcid=share
	# When the MWB started linked to the videos in March of 2018 the links looked like this:
	#  https://data.jw-api.org/mediator/finder?item=pub-mwbv_201803_1_VIDEO&lang=U
	#
	# But here is the June 2020 MWB:
	#  https://www.jw.org/finder?wtlocale=U&docid=202020204&srcid=share
	# The link format has changed:
	#  https://www.jw.org/open?lank=pub-mwbv_202006_1_VIDEO&wtlocale=U
	#
	def parse_video_url(self, url):
		url_obj = urlparse(url)
		query = dict(parse_qsl(url_obj.query))

		# Sharing link or link from MWB
		if url_obj.netloc == "www.jw.org" and url_obj.path in ("/finder", "/open"):
			if "lank" in query or "docid" in query:
				return query

		# Old format of links from MWB
		if url_obj.netloc == "data.jw-api.org" and url_obj.path == "/mediator/finder":
			if "item" in query:
				return {"lank": query["item"]}

		# Is this the URL for the generic LANK player used for featured videos?
		if url_obj.netloc == "www.jw.org" and url_obj.fragment:
			m = re.match(r"^([a-z]{2})/mediaitems/[^/]+/([^/]+)$", url_obj.fragment)
			if m:
				return {
					"wtlocale": iso_language_code_to_meps(m.group(1)),
					"lank": m.group(2),
					}

		return {}

