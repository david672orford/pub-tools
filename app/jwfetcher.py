from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qsl, urlencode, unquote, urljoin
import lxml.html
import json
import re
from time import sleep, time

class Fetcher:
	user_agent = "Mozilla/5.0"

	def __init__(self):
		self.last_request_time = 0

	# Send an HTTP GET request
	def get(self, url, query=None):
		left_to_wait = 2 - (time() - self.last_request_time)
		if left_to_wait > 0:
			sleep(left_to_wait)
		if query:
			url = url + '?' + urlencode(query)
		#print("Fetching %s..." % unquote(url))
		response = urlopen(Request(
			url,
			headers={'User-Agent': self.user_agent}
			))
		assert response.code == 200, "HTTP GET failed: %s %s" % (response.code, response.reason)
		self.last_request_time = time()
		return response

	# Send an HTTP GET request and parse the result as HTML.
	# Return the contents of the named container tag.
	def get_html(self, url, query=None):
		response = self.get(url, query=query)
		return lxml.html.parse(response).getroot()

	# Send an HTTP GET request and parse the result as JSON
	def get_json(self, url, query=None):
		response = self.get(url, query)
		return json.load(response)

	def dump_html(self, el): 
		print("=======================================================") 
		self.indent(el) 
		text = lxml.html.tostring(el, encoding="UNICODE") 
		print(text) 
 
	def dump_json(self, data):
		print("=======================================================") 
		text = json.dumps(data, indent=4, ensure_ascii=False)
		print(text)

	# Alter the whitespace in the element tree to indent the tabs 
	# https://web.archive.org/web/20200130163816/http://effbot.org/zone/element-lib.htm#prettyprint 
	@staticmethod 
	def indent(elem, level=0): 
		i = "\n" + level*"  " 
		if len(elem): 
			if not elem.text or not elem.text.strip(): 
				elem.text = i + "  " 
			if not elem.tail or not elem.tail.strip(): 
				elem.tail = i 
			for elem in elem: 
				Fetcher.indent(elem, level+1) 
			if not elem.tail or not elem.tail.strip(): 
				elem.tail = i 
		else: 
			if level and (not elem.tail or not elem.tail.strip()): 
				elem.tail = i 

