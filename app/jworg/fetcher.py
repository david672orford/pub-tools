import os
from urllib.request import urlopen, Request, HTTPHandler, HTTPSHandler, HTTPErrorProcessor, build_opener
from urllib.parse import urlparse, parse_qsl, urlencode, unquote, urljoin
from gzip import GzipFile
import lxml.html
import json
import re
from time import sleep, time
import logging

logger = logging.getLogger(__name__)

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

	# Minimum time between requests (in seconds)
	min_request_interval = 2.5

	# This API endpoint is used used to find the media files (MP3, MP4) which go
	# with a printed publication or the publication itself in downloadable
	# electronic form (such as PDF or Epub). Query string parameters:
	# * pub -- the publication abbreviation
	# * docid -- the MEPS document ID (can this really be used?)
	# * output -- set to "json"
	# * fileformat -- a comma-separated list of file extensions such as "m4v,mp4,3gp,mp3"
	# * alllangs -- generally "0"
	# * track -- song number
	# * langwritten -- language code ("U" for Russian)
	# * txtCMSLang -- language code (not clear how different from langwritten)
	pub_media_url = 'https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS'

	# Used for listing videos from JW Broadcasting by category
	# Query string parameters:
	# detailed=1 -- list subcategories and videos in this category
	# clientType=www -- Unknown
	mediator_categories_url = 'https://data.jw-api.org/mediator/v1/categories/{language}/{category}?detailed=1&clientType=www'

	# Used for getting the download link for a video when we know the language
	# we want and the video's Language Agnostic Natural Key (lank)
	mediator_items_url = 'https://b.jw-cdn.org/apis/mediator/v1/media-items/{language}/{video}'

	# Page in Watchtower Online Library which gives the study articles for a given week
	# It is necessary to parse the HTML to get the links to the articles and their docids.
	week_url = "https://wol.jw.org/en/wol/meetings/r1/lp-e/{year}/{week}"

	def __init__(self, language="U", cachedir="cache", debuglevel=0):
		self.language = language
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
			response = self.opener.open(request)
		else:
			response = self.no_redirects_opener.open(request)
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
		print("=======================================================") 
		Fetcher._indent(el) 
		text = lxml.html.tostring(el, encoding="UNICODE") 
		if filename:
			with open(filename, "w") as fh:
				fh.write(text)
		else:
			print(text) 
 
	@staticmethod 
	def dump_json(data):
		print("=======================================================") 
		text = json.dumps(data, indent=4, ensure_ascii=False)
		print(text)

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

	# Download a video or picture, store it in the cache directory, and return its path.
	def download_media(self, url):
		logger.info("Download media file %s...", url)
		cachefile = os.path.join(self.cachedir, os.path.basename(urlparse(url).path))
		if os.path.exists(cachefile):
			logger.info(" Satisfied from cache")
		else:
			#request = Request(url)
			#request.add_header("User-Agent", "Mozilla/5.0")
			#response = urlopen(request)
			response = self.get(url)
			total_expected = response.headers.get("Content-Length")
			with open(cachefile + ".tmp", "wb") as fh:
				total_recv = 0
				while True:
					chunk = response.read(16384)
					if not chunk:
						break
					fh.write(chunk)
					total_recv += len(chunk)
					logger.debug("%d of %s bytes received", total_recv, total_expected)
			os.rename(cachefile + ".tmp", cachefile)
			logger.info("Download complete %d bytes received", total_recv)
		return os.path.abspath(cachefile)

	# Get the URL of the video file for a song identified by number
	def get_song_video_url(self, song_number):
		media = self.get_json(self.pub_media_url,
			query = {
				'output': 'json',
				'pub': 'sjjm', 
				'fileformat': 'm4v,mp4,3gp,mp3',
				'alllangs': '0',
				'track': song_number,
				'langwritten': self.language,
				'txtCMSLang': self.language,
				}
			)
		video_url = media['files'][self.language]['MP4'][2]['file']['url']		# 480i
		return video_url

	# Given a link to a video from an article such as:
    #  https://www.jw.org/finder?lank=pub-jwbcov_201505_11_VIDEO&wtlocale=U
	# Extract the publication ID and language and use the mediator to get the
	# download URL for the MP4 file.
	def get_video_url(self, url):
		query = dict(parse_qsl(urlparse(url).query))
		media = self.get_json(self.mediator_items_url.format(
			language = query['wtlocale'],
			video = query['lank'],
			), query = { 'clientType': 'www' })
		return media['media'][0]['files'][2]['progressiveDownloadURL']

	# Find the EPUB download URL of a periodical
	def get_epub_url(self, pub_code, issue_code=None):
		logger.info("get_epub_url(%s, %s)", pub_code, issue_code)
		query = {
			'output': 'json',
			'pub': pub_code,
			'fileformat': 'EPUB',
			'alllangs': '0',
			'langwritten': self.language,
			'txtCMSLang': self.language,
			}
		if issue_code is not None:
			query['issue'] = issue_code
		media = self.get_json(self.pub_media_url, query=query)
		return media['files'][self.language]['EPUB'][0]['file']['url']

