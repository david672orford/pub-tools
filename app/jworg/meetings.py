from urllib.parse import urlparse, urljoin, parse_qsl, unquote, urlencode, urldefrag
from dataclasses import dataclass
import re
import traceback
import logging

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

class Article:
	def __init__(self, url, root):
		self.url = url
		self.root = root

		def xpath_one(container, path):
			elements = container.xpath(path)
			assert len(elements) == 1, f"Expected 1 match for \"{path}\", got {len(elements)}"
			return elements[0]

		self.title = xpath_one(root, "./head/title").text_content().strip()
		self.article_tag = xpath_one(root, ".//article")
		self.h1 = xpath_one(self.article_tag, ".//h1").text_content().strip()
		self.bodyTxt = xpath_one(self.article_tag, ".//div[@class='bodyTxt']")

		# TODO: Do we have a use for this? (It doesn't work yet either.)
		#self.thumbnail_url = self.article_tag.xpath(".//div[@class='cvr relatedImage']")[0].attrib["data-src"]

		# Get the publication ID code from the class of the <article> tag
		m = re.search(r" pub-(\S+) ", self.article_tag.attrib["class"])
		assert m, "No pub code"
		self.pub_code = m.group(1)

		# And the issue code
		m = re.search(r" iss-(\S+) ", self.article_tag.attrib["class"])
		self.issue_code = m.group(1) if m is not None else None

		# And the MEPS document ID
		m = re.search(r" docId-(\d+) ", self.article_tag.attrib["class"])
		assert m, "No pub dodid"
		self.docid = int(m.group(1))

		# Remove the section which has the page images
		#for el in self.article_tag.xpath(".//div[@id='docSubImg']"):
		#	el.getparent().remove(el)

# A single media item, such as a video, for use at a meeting
@dataclass
class MeetingMediaItem:

	# Name of this video, caption of image, name of article
	title: str

	# Abbreviation for this publication
	pub_code: str

	# "video", "image", "web" (for knowing how to display it in OBS)
	media_type: str

	# High-level media type such as "video", "image", "article" (for deciding whether we want it)
	is_a: str

	# The media file or web page
	media_url: str

	# Small image to represent it (optional)
	thumbnail_url: str = None

	# Section of Workbook (optional)
	section_title: str = None

	# Name of meeting part which links to this item (optional)
	part_title: str = None

	issue_code: str = None
	docid: int = None
	track: int = None

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

	# Fetch the indicated article from WWW.JW.ORG, parse the HTML,
	# pull out a few commonly needed things, and return it all in
	# an Article() object.
	def get_article(self, url:str):
		assert isinstance(url, str)
		return Article(url, self.get_html(url))

	# Fetch the web version of a Meeting Workbook lesson or Watchtower study
	# article, figure out which it is, and invoke the appropriate media
	# extractor function.
	def extract_media(self, url:str, callback):
		assert isinstance(url, str)
		assert callable(callback)

		article = self.get_article(url)
		callback(_("Article title: \"%s\"") % article.title)

		# Invoke the extractor for this publication (w=Watchtower, mwb=Meeting Workbook)
		extractor = getattr(self, f"extract_media_{article.pub_code}", None)
		assert extractor is not None, f"No extractor for {article.pub_code}"
		return extractor(article, callback)

	# Called from .extract_media() to extract media from a Watchtower study article
	def extract_media_w(self, article:Article, callback):
		assert isinstance(article, Article)
		assert callable(callback)
		for item in self.get_media(article.article_tag, article.url, {"song", "image", "video"}, callback):
			if item.pub_code is None:
				item.pub_code = article.pub_code
				item.issue_code = article.issue_code
			item.part_title = _("Watchtower Study")
			yield item

	# Called by .extract_media() to extract media from a Meeting Workbook
	def extract_media_mwb(self, article:Article, callback):
		assert isinstance(article, Article)
		assert callable(callback)

		# Convert the flat HTML structure to a list of the top-level sections.
		# Each section after the first is introduced by an <h2> tag.
		sections = [[None, []]]
		for el in article.bodyTxt:
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
				for item in self.get_media(el, article.url,
						{"song", "image", "video"},
						callback,
						# Include media in linked articles/chapters only in the last part of
						# the meeting where we want to include illustrations in the material
						# for the Congregation Bible Study.
						scrape_articles = (section_number==4),
						):
					if item.pub_code is None:
						item.pub_code = article.pub_code
						item.issue_code = article.issue_code
						item.docid = article.docid
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
				if pub.is_a in types:
					yield pub

				if pub.is_a == "article" and scrape_articles:
					callback(_("Getting media list from \"%s\"...") % pub.title)
					for item in self.get_media_from_linked_article(pub, item_tag.attrib.get("data-highlightrange"), linked_articles, callback):
						yield item

	# This is used to load the Congregation Bible Study material
	# TODO: Might a future publication have videos which are not presented as hyperlinked figures?
	def get_media_from_linked_article(self, pub:MeetingMediaItem, highlightrange:str, linked_articles:dict, callback):
		assert isinstance(pub, MeetingMediaItem)
		assert isinstance(highlightrange, str) or highlightrange is None
		assert isinstance(linked_articles, dict)
		article_href = pub.media_url

		# Load article, find figures, and attach them to paragraphs
		article = linked_articles.get(article_href)
		if article is None:
			article = linked_articles[article_href] = HighlightRange(self.get_article(article_href).article_tag)

		# If the URL has a fragment identifying a paragraph range,
		if highlightrange is not None and (m := re.match(r"^p(\d+)-p(\d+)$", highlightrange)):
			article_href = urldefrag(article_href).url
			start = int(m.group(1))
			end = int(m.group(2))
			figures = article.range_figures(start, end)
		else:
			figures = article.figures

		# Pull illustrations from the portion of the article selected above.
		for figure in figures:
			for item in self.get_media(figure.el, article_href, {"image", "video"}, callback):
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

		logattrib = dict(a.attrib).copy()
		logattrib["href"] = unquote(logattrib["href"])
		logger.info("Parsing <a %s> %s" % (logattrib, a.text_content().strip()))

		href = a.attrib["href"]
		if baseurl is not None:
			href = urljoin(baseurl, href)
		elif urlparse(href).scheme == "":
			raise ExceptionError("If baseurl is None, all URLs must be absolute")

		# Extract publication code
		# We may use it below to figure out what we've got.
		pub_code = re.match(r"^pub-(\S+)$", a.attrib.get("class",""))
		if pub_code is not None:
			pub_code = pub_code.group(1)

		# Extract MEPS document ID
		docid = re.match(r"^mid(\d+)$", a.attrib.get("data-page-id",""))
		if docid is not None:
			docid = int(docid.group(1))

		# In the Bible course links to videos and articles have thumbnail images
		el = a.find(".//span[@class='jsRespImg']")
		thumbnail_url = el.attrib.get("data-img-size-xs") if el is not None else None

		# We call this below. We are using it as a control structure.
		#def identify_pub(title, pub_code, docid, href, thumbnail_url, baseurl):
		def identify_pub():

			# A Video (but not all videos)
			# Sample <a> tag attributes:
			#  href="https://www.jw.org/finder?lank=pub-mwbv_202105_1_VIDEO&wtlocale=U"
			#  data-video="webpubvid://?pub=mwbv&issue=202105&track=1"
			#  data-jsonurl="https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS?langwritten=U&txtCMSLang=U&alllangs=1&output=json&fileformat=MP4%2CM4V%2C3GP&pub=mwbv&issue=202105&track=1"
			#  class="jsLinkedVideo"
			#  data-poster="https://assetsnffrgf-a.akamaihd.net/assets/ct/e781f8601f/images/video_poster.png"
			# Note the absence of a pub-X class.
			# IMPORTANT: Keep this before no-a-pub!
			if a.attrib.get("data-video") is not None:
				video_metadata = self.get_video_metadata(href)
				assert video_metadata is not None, f"No video_metadata: {href}"
				query = dict(parse_qsl(urlparse(a.attrib["data-video"]).query))
				return MeetingMediaItem(
					title = video_metadata["title"],
					pub_code = query["pub"],
					issue_code = query.get("issue"),
					track = int(query["track"]) if "track" in query else None,
					docid = query.get("docid"),		# FIXME: untested
					media_type = "video",
					is_a = "video",
					media_url = href,
					thumbnail_url = video_metadata["thumbnail_url"],
					)

			# Link to Bible passage, ignore
			if "jsBibleLink" in a.attrib.get("class","").split(" "):
				return "verse"

			# Footnote marker, ignore
			if a.attrib.get("class") == "footnoteLink":
				return "footnote"

			if pub_code is None:
				return "not-a-pub"

			# Publication: Song from Sing Out Joyfully to Jehovah
			if pub_code == "sjj":
				return self.get_song_from_a_tag(a)

			# Publication: Link to special player page for video series
			# TODO: Refine this test so we can get rid of the "ВИДЕО" hack.
			#       Note also that "ijwfq" is the code for online FAQ articles.
			if pub_code.startswith("ijw") or "ВИДЕО" in a.text_content():
				try:
					pub = self.get_ijw_from_a_tag(a, baseurl)
					if pub is not None:
						return pub
				except Exception as e:				# Fallback to webpage viewer
					logger.error(traceback.format_exc())
					return MeetingMediaItem(
						title = a.text_content().strip(),
						pub_code = pub_code,
						docid = docid,
						media_type = "web",
						is_a = "video",
						media_url = href,
						)

			# If we get here, we assume this is an article from which
			# the caller may wish to extract illustrations.
			return MeetingMediaItem(
				title = title if title is not None else a.text_content().strip(),
				pub_code = pub_code,
				docid = docid,
				media_type = "web",
				is_a = "article",
				media_url = href,
				thumbnail_url = thumbnail_url,
				)

		result = identify_pub()
		if type(result) is str:
			logger.info("Nothing extracted, is a %s", result)
			pub = None
			is_a = result
		else:
			logger.info("Extracted item: %s", result)
			pub = result
			is_a = pub.is_a

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
			part_title = song_text,
			title = metadata["title"],
			pub_code = "sjj %s" % song_number,
			media_type = "video",
			is_a = "song",
			media_url = "https://www.jw.org/finder?" + urlencode({
				"wtlocale": self.meps_language,
				"docid": a.attrib["data-page-id"][3:],
				"srcid": "share",
				}),
			thumbnail_url = metadata["thumbnail_url"],
			)

	# In most cases when the Meeting Workbook links to a video, it uses a sharing
	# URL with a "lank" parameter. This redirects to one of the Video on Demand
	# pages which were once part of tv.jw.org.
	#
	# But for links to videos from a series such as Become Jehovah's Friend,
	# the MWB tends to use the canonical URL of a custom player page instead. The <a>
	# tag includes a pub code and MEPS document ID, but there is no consistent
	# way to tell that the publication to which it points is a video rather than
	# an article.
	#
	# Attributes of the <a> tag:
	# * href -- long URL with localized text leading to player page
	# * class -- "pub-" + pub_code
	# * data-id-page -- "mid" + docid
	#
	# Examples in these Meeting Workbooks:
	# * https://www.jw.org/finder?wtlocale=U&docid=202024323&srcid=share (Become Jehovah's Friend, ijwpk)
	# * https://www.jw.org/finder?wtlocale=U&docid=202024408&srcid=share (Whiteboard Animation, ijwwb)
	#
	# The solution we came up with was to load the page and extract the information
	# we need to build a sharing URL.
	#
	# We used "ijw" in the name of this function because the pub codes found
	# in actual examples in the MWB started with these letters. Examination of
	# these player pages shows for other series shows that this is not always the case:
	#
	# |----------------------------------------------------------------------------------|
	# | Link and Player Class | VOD Pub Code | Series                                    |
	# |-----------------------|--------------|-------------------------------------------|
	# | pub-ijwpk             | pk           | Become Jehovah's Friend                   |
	# | pub-ijwwb             | -            | Whiteboard Animations                     |
	# | pub-pkon              | pkon         | Become Jehovah's Friend -- Original Songs |
	# | pub-sjj               | sjjm         | Sing Out Joyfully to Jehovah              |
	# |----------------------------------------------------------------------------------|
	#
	def get_ijw_from_a_tag(self, a, baseurl:str):
		assert isinstance(a, ET.ElementBase)
		assert a.tag == "a"
		assert isinstance(baseurl, str)

		# Follow the href to see whether it points to a video player page
		href = urljoin(baseurl, a.attrib["href"])
		article = self.get_article(href)

		# Look for a player. If none is found, bail out.
		player = article.article_tag.xpath(".//div[@class='jsIncludeVideo']")
		if len(player) == 0:
			return None
		player = player[0]

		# Extract the video's identifying information and build a sharing URL
		# Most of these pages lack a Share button, so we get the info from a tag
		# which seems to represent the place were the page Javascript should construct
		# the player. To see this, you will have to get the HTML directly from the site.
		# If you look for it in your browser, you will not find it since it will have
		# already been replaced.
		#
		# Example attributes:
		# * id="pk-44-video"
		# * data-page-id="mid501600124"
		# * data-jsonurl="https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS?output=json&amp;pub=pk&amp;fileformat=m4v%2Cmp4%2C3gp%2Cmp3&amp;alllangs=1&amp;track=44&amp;langwritten=U&amp;txtCMSLang=U"
		# * data-style=""
		# * data-poster="https://cms-imgp.jw-cdn.org/img/p/501600124/univ/art/501600124_univ_wsr_lg.jpg">
		# 
		if (m := re.match(r"^pub-([^-]+)-(\d+)$", player.attrib["id"])):			# Become Jehovah's Friend
			pub_code = m.group(1)
			track = int(m.group(2))
			docid = None
			lank = "pub-%s_%d_VIDEO" % (pub_code, track)
		elif (m := re.match(r"(\d+)-(\d+)-video$", player.attrib["id"])):			# Whiteboard Animations
			pub_code = None
			docid = int(m.group(1))
			track = int(m.group(2))
			lank = "docid-%s_%d_VIDEO" % (docid, track)
		else:
			raise AssertionError("Failed to parse player id: %s", player.attrib["id"])

		return MeetingMediaItem(
			title = article.h1,
			pub_code = pub_code,
			docid = docid,
			track = track,
			media_type = "video",
			is_a = "video",
			media_url = "https://www.jw.org/finder?" + urlencode({
				"wtlocale": self.meps_language,
				"lank": lank,
				"srcid": "share",
				}),
			thumbnail_url = player.attrib["data-poster"],
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
		if (figcaption := figure.find("./figcaption")) is not None:
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
			if pub is not None and pub.is_a in types:
				yield pub
				return

		# Loop over the images in this figure
		if "image" in types:
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
					title = caption or img.attrib.get("alt","").strip() or None,
					pub_code = None,			# caller can fill in, if needed
					media_type = "image",
					is_a = "image",
					media_url = src,
					thumbnail_url = span.attrib.get("data-img-size-xs"),
					)

