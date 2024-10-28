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

		# Get the publication ID code from the class of the <article> tag
		m = re.search(r" pub-(\S+) ", self.article_tag.attrib["class"])
		assert m, "JW.ORG pub code not found"
		self.pub_code = m.group(1)

		# And the issue code
		m = re.search(r" iss-(\S+) ", self.article_tag.attrib["class"])
		self.issue_code = m.group(1) if m is not None else None

		# And the MEPS document ID
		m = re.search(r" docId-(\d+) ", self.article_tag.attrib["class"])
		assert m, "JW.ORG docid not found"
		self.docid = int(m.group(1))

		# Remove the section which has the page images
		#for el in self.article_tag.xpath(".//div[@id='docSubImg']"):
		#	el.getparent().remove(el)

