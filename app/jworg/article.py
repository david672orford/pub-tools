import re

# Basic information about a web page
# This is used to:
# * See whether it is a player page
# * If not, get the title and thumbnail for the playlist
class WebpageMetadata:
	def __init__(self, url, root):
		self.url = url
		self.root = root

		el = root.xpath("./head/title")
		self.title = el[0].text if len(el) > 0 else None

		el = root.xpath(".//h1")
		self.h1 = el[0].text_content().strip() if len(el) > 0 else None

		el = root.xpath("./head/meta[@property='og:image']")
		self.thumbnail_url = el[0].attrib["content"] if len(el) > 0 else None

		# If this looks like an article from JW.ORG, extract the pub code.
		self.pub_code = None
		self.player = None
		article_tag = None
		if len(el := root.xpath(".//article")) > 0:
			print("  Found <article> tag")
			article_tag = el[0]
			if (m := re.search(r" pub-(\S+) ", article_tag.attrib.get("class",""))):
				print("  Found pub code")
				self.pub_code = m.group(1)
				if len(el := article_tag.xpath(".//div[@class='jsIncludeVideo']")) > 0:
					print("  Found video player")
					self.player = el[0].attrib["data-jsonurl"]
				# FIXME: disabled because turns WT articles into videos
				#elif len(el := article_tag.xpath(".//div[starts-with(@class,'jsAudioPlayer ')]")) > 0:
				#	print("found audio player")
				#	self.player = el[0].xpath(".//a")[0].attrib["href"]
				else:
					print("  No player found")
			else:
				print("  No pub code")
		else:
			print("  No <article> tag")

# Information about a web page which is expected to be an article from JW.ORG
# HTML is parsed and main sections identified
class Article:
	def __init__(self, url, root):
		self.url = url
		self.root = root

		def xpath_one(container, path):
			elements = container.xpath(path)
			assert len(elements) == 1, f"Expected 1 match for \"{path}\", got {len(elements)}"
			return elements[0]

		self.title = xpath_one(root, "./head/title").text
		self.main_tag = xpath_one(root, ".//main")
		self.article_tag = xpath_one(self.main_tag, ".//article")
		self.h1 = xpath_one(self.article_tag, ".//h1").text_content().strip()

		# The article body is generally enclosed in a <div class="bodyTxt">, but
		# there are exceptions such as Insight on the Scriptures.
		el = self.article_tag.xpath(".//div[@class='bodyTxt']")
		self.bodyTxt = el[0] if len(el) > 0 else self.article_tag

		og_image = self.root.xpath("./head/meta[@property='og:image']")
		self.thumbnail_url = og_image[0].attrib["content"] if len(og_image) > 0 else None

		# Identify the publication from the <article> tag classes
		self.pub_code: str = None
		self.issue_code: str = None
		self.docid: int = None
		for item in self.article_tag.attrib["class"].split():
			item = item.split("-",1)
			if len(item) == 2:
				name, value = item
				match name:
					case "pub":
						self.pub_code = value
					case "iss":
						self.issue_code = value
					case "docId":
						self.docid = int(value)
