from urllib.parse import urlparse, urljoin, parse_qsl, unquote, urlencode
from dataclasses import dataclass
import re, logging

from lxml import etree as ET

from .fetcher import Fetcher
from .hrange import HighlightRange
from ..utils.babel import gettext as _

logger = logging.getLogger(__name__)

# For translation
(
	_("image"),
	_("video"),
)

# A single media item, such as a video, for use at a meeting
@dataclass
class MeetingMediaItem:

	# Abbreviation for this publication
	pub_code: str

	# Name of this video, caption of image, name of article
	title: str

	# "video", "image", "web" (we will know how to display it)
	media_type: str

	# The media file or web page
	media_url: str

	# Small image to represent it (optional)
	thumbnail_url: str = None

	# Section of Workbook (optional)
	section_title: str = None

	# Name of meeting part which links to this item (optional)
	part_title: str = None

# Scan a Meeting Workbook week or Watchtower study article and return
# a list of the vidoes and pictures therein.
class MeetingLoader(Fetcher):

	# Get pointers to the Meeting Workbook and Watchtower articles to be
	# studied during a particular week. Though we later load the articles
	# from the main site <https://www.jw.org>, these are retrieved from
	# Watchtower Online Library <https://wol.jw.org> which is the only
	# place we found the weekly schedule online.
	def get_week(self, year:int, week:int):
		assert isinstance(year, int)
		assert isinstance(week, int)

		# Fetch the week's page from the meeting schedule on wol.jw.org.
		url = self.week_url.format(year=year, week=week)
		html = self.get_html(url)

		today_items = html.find_class("todayItems")[0]
		result = {}

		#------------------------------------------
		# Meeting Workbook
		#------------------------------------------
		mwb_div = today_items.find_class("pub-mwb")
		if len(mwb_div) > 0:
			mwb_div = mwb_div[0]
			# The MEPS docId is one of the classes of the todayItem <div> tag.
			result["mwb_docid"] = int(re.search(r" docId-(\d+) ", mwb_div.attrib["class"]).group(1))
		else:
			result["mwb_docid"] = None

		#------------------------------------------
		# Watchtower
		#------------------------------------------
		watchtower_div = today_items.find_class("pub-w")
		if len(watchtower_div) > 0:
			watchtower_div = watchtower_div[0]
			# Follow the link. The MEPS docId is at the end of the URL to which we are redirected.
			watchtower_url = urljoin(url, watchtower_div.find_class("itemData")[0].xpath(".//a")[0].attrib["href"])
			response = self.get(watchtower_url, follow_redirects=False)
			result["watchtower_docid"] = response.geturl().split('/')[-1]
		else:
			result["watchtower_docid"] = None

		return result

	# Given a MEPS document ID, construct a sharing URL for an article.
	# Sharing URL's redirect to the actual webpage of the article.
	def meeting_url(self, docid):
		return "https://www.jw.org/finder?wtlocale={wtlocale}&docid={docid}&srcid=share".format(
			docid = docid,
			wtlocale = self.meps_language,
			)

	# Fetch the web version of a Meeting Workbook lesson or Watchtower study
	# article, figure out which it is, and invoke the appropriate media
	# extractor function.
	def extract_media(self, url:str, callback):
		assert isinstance(url, str)
		assert callable(callback)

		container = self.get_article_html(url)
		assert container.tag == "article"

		h1 = container.xpath(".//h1")
		assert len(h1) == 1
		title = h1[0].text_content().strip()
		callback(_("Article title: \"%s\"") % title)

		# Get the publication ID code from the class of the <article> tag
		m = re.search(r" pub-(\S+) ", container.attrib["class"])
		assert m, "No pub code"
		pub_code = m.group(1)

		# Invoke the extractor for this publication (w=Watchtower, mwb=Meeting Workbook)
		extractor = getattr(self, f"extract_media_{pub_code}", None)
		assert extractor is not None, f"No extractor for {pub_code}"
		return extractor(pub_code, container, url, callback)

	# Fetch the indicated article from WWW.JW.ORG, parse the HTML,
	# and return the <article> tag's content.
	def get_article_html(self, url:str):
		assert isinstance(url, str)

		html = self.get_html(url)

		container = html.xpath(".//article")
		assert len(container) == 1, "Found %d main containers!" % len(container)
		container = container[0]

		# Remove the section which has the page images
		for el in container.xpath(".//div[@id='docSubImg']"):
			el.getparent().remove(el)

		return container

	# Called from .extract_media() to extract media from a Watchtower study article
	def extract_media_w(self, pub_code:str, container, baseurl:str, callback):
		assert isinstance(pub_code, str)
		assert isinstance(container, ET.ElementBase)
		assert isinstance(baseurl, str)
		assert callable(callback)
		for item in self.get_media(container, baseurl, {"song", "image", "video"}, callback):
			if item.pub_code is None:
				item.pub_code = pub_code
			item.part_title = _("Watchtower Study")
			yield item

	# Called by .extract_media() to extract media from a Meeting Workbook
	def extract_media_mwb(self, pub_code:str, container, baseurl:str, callback):
		assert isinstance(pub_code, str)
		assert isinstance(container, ET.ElementBase)
		assert isinstance(baseurl, str)
		assert callable(callback)

		# Since we want to parse the structure, shift our focus to the actual content container.
		container = container.xpath(".//div[@class='bodyTxt']")
		assert len(container) == 1
		container = container[0]

		# Convert the flat HTML structure to a list of the top-level sections.
		# Each section after the first is introduced by an <h2> tag.
		sections = [[None, []]]
		for el in container:
			h2 = el.xpath("./h2")
			if h2:
				sections.append([h2[0].text_content().strip(), []])
			else:
				sections[-1][1].append(el)

		# Loop through the sections of the Workbook page for a Midweek Meeting
		# The Sections by section_number
		# 1 -- Opening Song and Prayer
		# 2 -- <h2>СОКРОВИЩА ИЗ СЛОВА БОГА</h2>
		# 3 -- <h2>ОТТАЧИВАЕМ НАВЫКИ СЛУЖЕНИЯ</h2>
		# 4 -- <h2>ХРИСТИАНСКАЯ ЖИЗНЬ</h2>
		section_number = 0
		for section_title, section_els in sections:
			section_number += 1
			part_title = None
			logger.info("Top-level section: %d %s", section_number, section_title)

			# Loop through the HTML elements in each section
			part_number = 0		# <-- used only for log messages
			for el in section_els:
				#
				# Examples of How Songs and Meeting Parts are Formatted
				# 
				# <h3>
				#   <a><strong>Song N</strong></a>
				# </h3>
				#
				# or
				#
				# <div>
				#   <h3>Part Title</h3>
				#   <div></div>
				#   <div></div>
				# </div>
				#
				# or
				#
				# <h3>Part Title</h3>
				# <div></div>
				#
				if el.tag == "h3":
					part_number += 1
					# If this is a song, we process pub links within the <h3>.
					song_link = el.xpath(".//a[@class='pub-sjj']")
					if song_link:
						part_title = song_link[0].text_content().strip()
					# If not, the title applies to the <div>'s which follow.
					else:
						part_title = el.text_content().strip()
						continue
				else:
					h3 = el.xpath(".//h3")
					if h3:
						part_number += 1
						part_title = h3[0].text_content().strip()
				logger.info("Section %d, part %d \"%s\"", section_number, part_number, part_title)

				# Pull media items from this part
				for item in self.get_media(el, baseurl,
						{"song", "image", "video"},
						callback,
						# Include media in linked articles/chapters only in the last part of
						# the meeting where we want to include illustrations in the material
						# for the Congregation Bible Study.
						scrape_articles = (section_number==4),
						):
					if item.pub_code is None:
						item.pub_code = pub_code
					item.section_title = section_title
					item.part_title = part_title
					yield item

				# End of part loop
			# End of Workbook section loop

	# Extract media of the specified types from the HTML container provided.
	# If scrape_articles is True, follow links and to other documents and extract
	# their media too.
	def get_media(self, container, baseurl:str, types:set, callback, scrape_articles:bool=False):
		assert isinstance(container, ET.ElementBase)
		assert isinstance(baseurl, str)
		assert isinstance(types, set)
		assert callable(callback)
		assert isinstance(scrape_articles, bool)
		context = ET.iterwalk(container, events={"start"}, tag={"a", "figure"})
		linked_articles = {}
		for action, item_tag in context:

			if item_tag.tag == "figure":
				if "image" in types:
					for item in self.get_figure_items(item_tag, baseurl, types):
						yield item
				# Don't let <a> handler see <a>'s in <figure>'s since get_figure_items() handles them.
				context.skip_subtree()

			elif item_tag.tag == "a":
				pub = self.get_pub_from_a_tag(item_tag, baseurl)
				if pub is None:
					logger.warning("Unrecognized link: %s", item_tag.attrib)
					continue
	
				# We always keep songs and videos
				if pub.media_type in types:
					yield pub
	
				if pub.media_type == "web" and scrape_articles:
					callback(_("Getting media list from \"%s\"...") % pub.title)
					for item in self.get_media_from_linked_article(pub, item_tag.attrib.get("data-highlightrange"), linked_articles, callback):
						yield item

	# This is used to load the Congregation Bible Study material
	def get_media_from_linked_article(self, pub:MeetingMediaItem, highlightrange:str, linked_articles:dict, callback):
		assert isinstance(pub, MeetingMediaItem)
		assert isinstance(highlightrange, str)
		assert isinstance(linked_articles, dict)
		article_href = pub.media_url

		# Load article, find figures, and attach them to paragraphs
		article = linked_articles.get(article_href)
		if article is None:
			article = linked_articles[article_href] = HighlightRange(self.get_article_html(article_href))

		# If the URL has a fragment identifying a paragraph range,
		if highlightrange is not None and (m := re.match(r"^p(\d+)-p(\d+)$", highlightrange)):
			article_href = article_href.split("#",1)[0]
			start = int(m.group(1))
			end = int(m.group(2))
			containers = article.range_figures(start, end)
		else:
			containers = article.figures

		# Pull illustrations from the portion of the article selected above.
		for container in containers:
			for item in self.get_media(container, article_href, {"image", "video"}, callback):
				if item.pub_code is None:
					item.pub_code = pub.pub_code
				yield item

	# If the <a> tag supplied points to a publications or media item from
	# JW.ORG, return a MeetingMediaItem object (or its subclass). Otherwise,
	# return None.
	# If baseurl is supplied, it will be used to canonicalize relative hrefs.
	def get_pub_from_a_tag(self, a, baseurl:str, title:str=None):
		assert isinstance(a, ET.ElementBase)
		assert a.tag == "a"
		assert isinstance(baseurl, str) or baseurl is None

		logger.info("Pub <a> tag: href=\"%s\" %s", unquote(a.attrib["href"]), str(a.attrib))
		pub = None

		# This is for the log message which is printed after we break out of this 'loop'
		is_a = None

		# In the Bible course links to videos and articles have thumbnail images
		thumbnail = a.find(".//span[@class='jsRespImg']")
		thumbnail_url = thumbnail.attrib.get("data-img-size-xs") if thumbnail is not None else None

		# Not an actual loop. We always break out during the first iteration.
		while True:

			# A Video (but not all videos)
			# Sample <a> tag attributes:
			#  data-video="webpubvid://?pub=mwbv&issue=202105&track=1"
			#  href="https://www.jw.org/finder?lank=pub-mwbv_202105_1_VIDEO&wtlocale=U"
			# IMPORTANT: Keep this at the top since there may not be a pub code!
			if a.attrib.get("data-video") is not None:
				video_metadata = self.get_video_metadata(a.attrib["href"])
				assert video_metadata is not None, a.attrib["href"]
				query = dict(parse_qsl(urlparse(a.attrib["href"]).query))
				pub = MeetingMediaItem(
					# If there is no pub code, this is probably a special video cut for the
					# publication in which it is embedded. Leave it None for now.
					pub_code = None if "docid" in query else re.sub(r"^pub-([^_]+)_.+$", lambda m: m.group(1), query["lank"]),
					title = video_metadata["title"],
					media_type = "video",
					media_url = a.attrib["href"],
					thumbnail_url = video_metadata["thumbnail_url"],
					)
				is_a = "video"
				break

			# Link to Bible passage, ignore
			if "jsBibleLink" in a.attrib.get("class","").split(" "):
				is_a = "verse"
				break

			# Footnote marker, ignore
			if a.attrib.get("class") == "footnoteLink":
				is_a = "footnote"
				break

			# Extract publication code
			# We will use it below to figure out what we've got.
			pub_code = re.match(r"^pub-(\S+)$", a.attrib.get("class",""))
			if pub_code is None:
				is_a = "not-a-pub"
				break
			pub_code = pub_code.group(1)

			# Extract MEPS document ID
			# (Disabled because has not proved useful so far)
			#docid = re.match(r"^mid(\d+)$", a.attrib.get("data-page-id",""))
			#if docid is None:
			#	is_a = "no-docid"
			#	break
			#docid = docid.group(1)

			# Publication: Song from Sing Out Joyfully to Jehovah
			if pub_code == "sjj":
				pub = self.get_song_from_a_tag(a)
				is_a = "song"
				break

			# Publication: Link to special player page for video series
			# FIXME: language-specific hack
			if "ВИДЕО" in a.text_content():
				try:
					pub = self.get_video_episode_item_from_a_tag(a, baseurl)
					is_a = "video"
				except Exception as e:				# Fallback to webpage viewer
					media_url = a.attrib["href"]
					if baseurl is not None:
						media_url = urljoin(baseurl, media_url)
					pub = MeetingMediaItem(
						pub_code = pub_code,
						title = a.text_content().strip(),
						media_type = "web",
						media_url = media_url,
						)
					is_a = "video"
				break

			# If we get here, we assume this is an article from which
			# the caller may wish to extract illustrations.
			pub = MeetingMediaItem(
				pub_code = pub_code,
				title = title if title is not None else a.text_content().strip(),
				media_type = "web",
				media_url = urljoin(baseurl, a.attrib["href"]),
				thumbnail_url = thumbnail_url,
				)
			is_a = "article"
			break

		logger.info("Extracted item: %s \"%s\" (%s)" % (str(a.attrib.get("class")).strip(), a.text_content().strip(), is_a))
		return pub

	# Handle a link to a song from Sing Out Joyfully to Jehovah
	def get_song_from_a_tag(self, a):
		assert isinstance(a, ET.ElementBase)
		assert a.tag == "a"

		song_text = a.text_content().strip()
		song_number = re.search(r"(\d+)$", song_text)
		assert song_number is not None, "Song number: %s" % repr(song_number)
		song_number = int(song_number.group(1))
		# NOTE: We switched from the Pub Media API to the Mediator API in October
		# of 2024 because 1) we wanted 16:9 thumbnails, and 2) the thumbnails for
		# all but the new songs had empty URL's.
		metadata = self.get_video_metadata(query={"lank": f"pub-sjjm_{song_number}_VIDEO"})
		return MeetingMediaItem(
			pub_code = "sjj %s" % song_number,
			part_title = song_text,
			title = metadata["title"],
			media_type = "video",
			media_url = "https://www.jw.org/finder?" + urlencode({
				"wtlocale": self.meps_language,
				"docid": a.attrib["data-page-id"][3:],
				"srcid": "share",
				}),
			thumbnail_url = metadata["thumbnail_url"],
			)

	# When the Workbook links to certain videos from a series such as
	# Become Jehovah's Friend, it may use the URL of an alternative player
	# page rathan than the sharing URL. The player page may also lack a
	# sharing link. This function fetches the player page, finds the
	# embedded player, and extracts the publication code and track number,
	# and builds the sharing URL.
	def get_video_episode_item_from_a_tag(self, a, baseurl:str):
		assert isinstance(a, ET.ElementBase)
		assert a.tag == "a"
		assert isinstance(baseurl, str)

		href = a.attrib["href"]
		if baseurl is not None:
			href = urljoin(baseurl, href)
		container = self.get_article_html(href)
		title = container.xpath(".//h1")[0].text_content().strip()
		thumbnail = container.xpath(".//div[contains(@class,'jsVideoPoster')]")[0].attrib["data-src"]
		player = container.xpath(".//div[@class='jsIncludeVideo']")[0]
		m = re.match(r"^(.+)-(\d+)-video$", player.attrib.get("id"))
		pub_code = m.group(1)
		track = int(m.group(2))
		return MeetingMediaItem(
			pub_code = "%s %d" % (pub_code, track),
			title = title,
			media_type = "video",
			media_url = "https://www.jw.org/finder?" + urlencode({
				"wtlocale": self.meps_language,
				"lank": "pub-%s_%d_VIDEO" % (pub_code, track),
				"srcid": "share",
				}),
			thumbnail_url = thumbnail,
			)

	# Given a <figure> tag extract the MediaMedia item
	# Can return:
	# * A single illustration
	# * Each illustration in an image carousel
	# * A link to a video with thumbnail image
	# * A link to an article with thumbnail image
	# 
	def get_figure_items(self, figure, baseurl:str, types:set):
		assert isinstance(figure, ET.ElementBase)
		assert figure.tag == "figure"
		assert isinstance(baseurl, str)
		assert isinstance(types, set)
		self.dump_html(figure)

		#
		# Examples (before modification by the Javascript):
		#
		# Illustration
		#
		# <div id="f1" ...>
		#  <figure>
		#    <span class="jsRespImg" data-img-type="cnt" data-img-att-class="south_center" data-img-att-alt="..." ...>
		#     <noscript>
		#      <img src="..." alt="...">
		#     </noscript>
		#    </span>
		#   <figcaption>
		#    <p id="pN" data-pid="N" class="pN">...</p>
		#   </figcaption>
		#  </figure>
		# </div>
		#
		# * The <figcaption> may be absent.
		# * There may be multiple <span> elements for an image carousel
		#
		# Link to Video with Poster Frame
		#
		# <div id="f2" ... >
		#  <figure>
		#   <a href="..." data-video="..." ...>
		#    <span class="jsRespImg" data-img-type="cnt" data-img-att-class="suppressZoom" ...>
		#     <noscript>
		#      <img src="..." alt="" class="suppressZoom">
		#     </noscript>
		#    </span>
		#   </a>
		#  </figure>
		# </div>
		#
		# Link to Article with Image and Blurb
		#
		# <div id="tt103">
		#  <div id="f3">
		#   <figure>
		#    <a class="pub-XX" data-page-id="..." href="...">
		#     <span class="jsRespImg" data-img-att-alt="..." ...>
		#      <noscript>
		#       <img src="..." alt="...">
		#      </noscript>
		#     </span>
		#    </a>
		#   </figure>
		#  </div>
		#  <div id="tt104">
		#   <p>Прочитайте как...</p>
		#   <p>
		#    <a class="pub-XX" ...>Article blurb</a>
		#   </p>
		#  </div>
		# </div>
		#
		# Examples of these figure types can be found here:
		# https://www.jw.org/finder?wtlocale=U&docid=1102021202&srcid=share
		#
		link = figure.find("./a")

		# Get the figure caption
		caption = None
		if figcaption := figure.find("./figcaption"):
			caption = figcaption.text_content()
			# remove footnote marker from end of caption
			caption = caption.strip().removesuffix("*").rstrip()

		# If there is no <figcaption>, but the next neighbor of the <figure> has
		# a <a> with the same href or the same data-video, that is the blurb.
		# Use it's text as the caption.
		elif link is not None and (blurb_div := figure.getparent().getnext()) is not None:
			href = link.attrib.get("href")
			if len(blurb_a := blurb_div.xpath(".//a[@href='%s']" % href)) > 0 \
					or ((video := link.attrib.get("data-video")) is not None and \
						len(blurb_a := blurb_div.xpath(".//a[@data-video='%s']" % video)) > 0):
				caption = blurb_a[0].text_content().strip()

		# Is this image a link to a video or article?
		# This is used in the Bible course for supplementary material.
		if link is not None:
			pub = self.get_pub_from_a_tag(link, baseurl, title=caption)
			if pub is not None and pub.media_type in types:
				yield pub
				return

		# Loop over the images in this figure
		for span in figure.findall(".//span[@class='jsRespImg']"):
			img = span.find("./noscript/img")
			assert span is not None and img is not None

			# Take the highest resolution version we can get
			for variant in ("data-zoom", "data-img-size-lg", "data-img-size-md", "data-img-size-sm", "data-img-size-xs"):
				src = span.attrib.get(variant)
				if src is not None:
					break
			else:
				raise AssertionError("No image source in jsRespImg: %s" % str(span.attrib))

			yield MeetingMediaItem(
				pub_code = None,			# caller can fill in, if needed
				title = caption or img.attrib.get("alt","").strip() or None,
				media_type = "image",
				media_url = src,
				thumbnail_url = span.attrib.get("data-img-size-xs"),
				)

