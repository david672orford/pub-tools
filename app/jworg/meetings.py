from urllib.parse import urlparse, urljoin, parse_qsl, unquote, urlencode
from dataclasses import dataclass
import re, logging

from .fetcher import Fetcher
from ..utils.babel import gettext as _

logger = logging.getLogger(__name__)

# For translation
(
	_("image"),
	_("video"),
)

# A single media item, such as a video, for use at a meeting
@dataclass
class MeetingMedia:

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

# An article from which we may want to extract MeetingMedia items
class MeetingMediaArticle(MeetingMedia):
	pass

# Scan a Meeting Workbook week or Watchtower study article and return
# a list of the vidoes and pictures therein.
class MeetingLoader(Fetcher):

	# Get pointers to the Meeting Workbook and Watchtower articles
	# to be studied during a particular week
	def get_week(self, year, week):

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

			# URL of meeting workbook page on wol.jw.org
			result["mwb_url"] = urljoin(url, mwb_div.find_class("itemData")[0].xpath('.//a')[0].attrib['href'])

			# The MEPS docId is one of the classes of the todayItem <div> tag.
			result["mwb_docid"] = int(re.search(r" docId-(\d+) ", mwb_div.attrib["class"]).group(1))

		else:
			result["mwb_url"] = None
			result["mwb_docid"] = None

		#------------------------------------------
		# Watchtower
		#------------------------------------------
		watchtower_div = today_items.find_class("pub-w")
		if len(watchtower_div) > 0:
			watchtower_div = watchtower_div[0]

			# URL of Watchtower article on wol.jw.org
			result["watchtower_url"] = urljoin(url, watchtower_div.find_class("itemData")[0].xpath(".//a")[0].attrib["href"])

			# Follow the link. The MEPS docId at the end of the URL to which we are redirected.
			response = self.get(result["watchtower_url"], follow_redirects=False)
			result["watchtower_docid"] = response.geturl().split('/')[-1]

		else:
			result["watchtower_url"] = None
			result["watchtower_docid"] = None

		return result

	# Fetch the web version of a Meeting Workbook lesson or Watchtower study
	# article, figure out which it is, and invoke the appropriate media
	# extractor function.
	def extract_media(self, url:str, callback=None):
		container = self.get_article_html(url)
		callback(_("Article title: \"%s\"") % container.xpath(".//h1")[0].text_content().strip())

		# Invoke the extractor for this publication (w=Watchtower, mwb=Meeting Workbook)
		m = re.search(r" pub-(\S+) ", container.attrib["class"])
		assert m, "No pub code"
		return getattr(self, "extract_media_%s" % m.group(1))(url, container, callback)

	# Fetch the indicated article from WWW.JW.ORG, parse the HTML, and return
	# the article content. Normally this is the the content of the <article>
	# tag. But, if main is True, return the contents of the <main> tag instead.
	def get_article_html(self, url:str, main:bool=False):
		html = self.get_html(url)

		container = html.xpath(".//main" if main else ".//article")
		assert len(container) == 1, "Found %d main containers!" % len(container)
		container = container[0]

		# Remove the section which has the page images
		for el in container.xpath(".//div[@id='docSubImg']"):
			el.getparent().remove(el)

		return container

	# Handler for a lesson page from the Meeting Workbook
	# Called by .extract_media()
	def extract_media_mwb(self, baseurl:str, container, callback):
		container = container.xpath(".//div[@class='bodyTxt']")[0]

		# Convert the flat HTML structure to a list of the top-level sections
		sections = [[None, []]]
		for el in container:
			h2 = el.xpath("./h2")
			if h2:
				sections.append([h2[0].text_content().strip(), []])
			else:
				sections[-1][1].append(el)

		# Loop through the sections of the Workbook page yielding the media items as we go
		section_number = 0
		for section_title, section_els in sections:
			section_number += 1
			part_title = None
			logger.info("Top-level section: %d %s", section_number, section_title)

			# Loop through the HTML elements in this section
			part_number = 0
			for el in section_els:
				article_href_dedup = set()

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

				# Illustrations in this HTML element
				for illustration in self.extract_illustrations("mwb", "Тетрядь", el):
					illustration.section_title = section_title
					illustration.part_title = part_title
					yield illustration

				# Go through all of the hyperlinks in this HTML element
				for a in el.xpath(".//a"):
					pub = self.get_pub_from_a_tag(a, baseurl)
					if pub is not None:
						if type(pub) is not MeetingMediaArticle:
							pub.section_title = section_title
							pub.part_title = part_title
							yield pub

						elif section_number == 4:	# Христианская жизнь
							callback(_("Getting media list from \"%s\"...") % pub.title)

							# If we have not scraped this article for illustrations yet, do so now.
							# TODO: interpret the paragraph ranges in the URL fragment
							article_href = urljoin(baseurl, a.attrib["href"])
							article_href_nofragment = article_href.split("#")[0]
							if not article_href_nofragment in article_href_dedup:

								# Get the content of the article's <main> tag and extract illustrations
								article_main = self.get_article_html(article_href, main=True)
								for illustration in self.extract_illustrations(pub.pub_code, pub.title, article_main):
									illustration.section_title = section_title
									illustration.part_title = part_title
									yield illustration

								article_href_dedup.add(article_href_nofragment)

	# Figure out to what publication an <a> tag points
	def get_pub_from_a_tag(self, a, baseurl:str):
		assert a.tag == "a"
		logger.info("Pub <a> tag: href=\"%s\" %s", unquote(a.attrib["href"]), str(a.attrib))
		pub = None

		# This is for the log message which is printed after we break out of this 'loop'
		is_a = None

		# Not an actual loop. We always break out during the first iteration.
		while True:

			# Link to Bible passage, ignore
			if "jsBibleLink" in a.attrib.get("class","").split(" "):
				is_a = "verse"
				break

			# Footnote marker, ignore
			if a.attrib.get("class") == "footnoteLink":
				is_a = "footnote"
				break

			# A Video (but not all videos)
			# Sample <a> tag attributes:
			#  data-video="webpubvid://?pub=mwbv&issue=202105&track=1"
			#  href="https://www.jw.org/finder?lank=pub-mwbv_202105_1_VIDEO&wtlocale=U"
			if a.attrib.get("data-video") is not None:
				video_metadata = self.get_video_metadata(a.attrib["href"])
				assert video_metadata is not None, a.attrib["href"]
				query = dict(parse_qsl(urlparse(a.attrib["href"]).query))
				pub = MeetingMedia(
					pub_code = pub_code if "docid" in query else re.sub(r"^pub-([^_]+)_.+$", lambda m: m.group(1), query["lank"]),
					title = video_metadata["title"],
					media_type = "video",
					media_url = a.attrib["href"],
					thumbnail_url = video_metadata["thumbnail_url"],
					)
				is_a = "video"
				break

			# Extract publication code
			# We will use it below to figure out what we've got.
			pub_code = re.match(r"^pub-(\S+)$", a.attrib.get("class",""))
			if pub_code is None:
				is_a = "not-a-pub"
				break
			pub_code = pub_code.group(1)

			# Extract MEPS document ID
			# So far this has not proved useful
			#docid = re.match(r"^mid(\d+)$", a.attrib.get("data-page-id",""))
			#if docid is None:
			#	is_a = "no-docid"
			#	break
			#docid = docid.group(1)

			# Publication: Song from Sing Out Joyfully to Jehovah
			if pub_code == "sjj":
				pub = self.make_song_item(a)
				is_a = "song"
				break

			# Publication: Link to special player page for video series
			if "ВИДЕО" in a.text_content():
				try:
					pub = self.make_video_episode_item(a, baseurl)
					is_a = "video"
				except Exception as e:
					pub = MeetingMedia(
						pub_code = pub_code,
						title = a.text_content().strip(),
						media_type = "web",
						media_url = urljoin(baseurl, a.attrib["href"]),
						)
					is_a = "video"
				break

			# If we get here, we assume this is an article from which the caller
			# might wish to extract illustrations.
			pub = MeetingMediaArticle(
				pub_code = pub_code,
				title = a.text_content().strip(),
				media_type = "web",
				media_url = a.attrib["href"],
				)
			is_a = "article"
			break

		logger.info("Extracted item: %s \"%s\" (%s)" % (str(a.attrib.get("class")).strip(), a.text_content().strip(), is_a))
		return pub

	# Handler for a Watchtower study article
	# Called from .extract_media()
	def extract_media_w(self, baseurl, container, callback):

		# <a class='pub-sjj' is a song.
		# FIXME: There should always be two, opening and closing, however, the study
		# article for the week of June 12, 2023 has additional songs in a footnote
		# which confuses things.
		songs = container.xpath(".//a[@class='pub-sjj']")
		if len(songs) != 2:
			logger.warning("Found %d songs when two expected" % len(songs))

		yield self.make_song_item(songs[0])

		for illustration in self.extract_illustrations("w", "СБ", container):
			yield illustration

		yield self.make_song_item(songs[1])

	# Handle a link to a song from Sing Out Joyfully to Jehovah
	def make_song_item(self, a):
		song_text = a.text_content().strip()
		song_number = re.search(r"(\d+)$", song_text)
		assert song_number is not None, "Song number: %s" % repr(song_number)
		song_number = int(song_number.group(1))
		# NOTE: We switched from the Pub Media API to the Mediator API in October
		# of 2024 because 1) we wanted 16:9 thumbnails, and 2) the thumbnails for
		# all but the new songs had empty URL's.
		metadata = self.get_video_metadata(query={"lank": f"pub-sjjm_{song_number}_VIDEO"})
		return MeetingMedia(
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
	def make_video_episode_item(self, a, baseurl:str):
		container = self.get_article_html(urljoin(baseurl, a.attrib["href"]))
		title = container.xpath(".//h1")[0].text_content().strip()
		thumbnail = container.xpath(".//div[contains(@class,'jsVideoPoster')]")[0].attrib["data-src"]
		player = container.xpath(".//div[@class='jsIncludeVideo']")[0]
		m = re.match(r"^(.+)-(\d+)-video$", player.attrib.get("id"))
		pub_code = m.group(1)
		track = int(m.group(2))
		return MeetingMedia(
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

	# Find the illustrations (<figure> tags) from an HTML container tag.
	# The Watchtower extractor runs this on the whole article.
	# The Meeting Workbook extractor runs this on sections of the Workbook
	# and on the Bible Study material.
	def extract_illustrations(self, pub_code, article_title, container):
		#self.dump_html(container)

		#
		# Examples (before modification by the Javascript):
		#
		# Article head illustration in Watchtower:
		#
		# <figure class="article-top-related-image jwac textSizeIncrement">
		#   <span class="jsRespImg" data-img-type="lsr" data-img-att-alt="..." ...>
		#    <noscript>
		#     <img src="..." alt="...">
		#    </noscript>
		#   </span>
		# </figure>
		#
		# Article head illustration in Meeting Workbook
		#
		# <figure>
		#   <span class="jsRespImg" data-img-type="cnt" data-img-att-class="south_center" data-img-att-alt="..." ...>
		#    <noscript>
		#     <img src="..." alt="...">
		#    </noscript>
		#   </span>
		# </figure>
		#
		# Internal illustration with caption:
		#
		# <figure>
		#  <span class="jsRespImg" data-img-type="cnt" data-img-att-class="south_center" data-img-att-alt="..." ...>
		#   <noscript>
		#    <img src="..." alt="...">
		#   </noscript>
		#  </span>
		#  <figcaption>
		#   <p id="pN" data-pid="N" class="pN">...</p>
		#  </figcaption>
		# </figure>
		#
		# There will sometimes be multiple <span>'s, one for each image in a carousel.
		#
		# Image link to video with poster:
		#
		# <figure>
		#  <a href="..." data-video="..." ...>
		#   <span class="jsRespImg" data-img-type="cnt" data-img-att-class="suppressZoom" ...>
		#    <noscript>
		#     <img src="..." alt="" class="suppressZoom">
		#    </noscript>
		#   </span>
		#  </a>
		# </figure>
		#
		# Image link to article with context:
		#
		# <div>
		#  <div>
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
		#  <div>
		#   <p>...</p>
		#   <p>
		#    <a class="pub-XX" ...>...</a>
		#   </p>
		#  </div>
		# </div>
		#
		n = 0
		for figure in container.xpath(".//figure"):
			self.dump_html(figure)
			n += 1
			link = figure.find("./a")

			figcaption = figure.find("./figcaption")
			if figcaption is not None:
				# Caption text with footnote marker stripped from end and whitespace from both ends
				caption = figcaption.text_content().strip().removesuffix("*").rstrip()
			elif link is not None and link.attrib.get("class","").startswith("pub-"):
				caption_div = figure.getparent().getnext()
				caption = caption_div.xpath(".//a[@class='%s']" % link.attrib.get("class"))[0].text_content()
			else:
				caption = None

			# Is this image linked to something?
			if link is not None:

				# Is this image linked to a video?
				if link.attrib.get("data-video") is not None:
					video_metadata = self.get_video_metadata(link.attrib["href"])
					assert video_metadata is not None, link.attrib["href"]
					query = dict(parse_qsl(urlparse(link.attrib["href"]).query))
					yield MeetingMedia(
						# If specified by docid, assume video is part of publication, otherwise extract a pub ID from LANK
						pub_code = pub_code if "docid" in query else re.sub(r"^pub-([^_]+)_.+$", lambda m: m.group(1), query["lank"]),
						title = caption if caption is not None else video_metadata["title"],
						media_type = "video",
						media_url = link.attrib["href"],
						thumbnail_url = video_metadata["thumbnail_url"],
						)
					continue

				# Article
				else:
					span = figure.find(".//span[@class='jsRespImg']")
					yield MeetingMedia(
						pub_code = None,
						title = caption,
						media_type = "web",
						media_url = urljoin("https://www.jw.org", link.attrib['href']),
						thumbnail_url = span.attrib.get("data-img-size-xs"),
						)
					continue

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

				if caption:
					media_title = caption
				else:
					media_title = img.attrib.get("alt","").strip()

				if media_title == "":
					media_title = "%s №%d" % (article_title, n)

				yield MeetingMedia(
					pub_code = pub_code,
					title = media_title,
					media_type = "image",
					media_url = src,
					thumbnail_url = span.attrib.get("data-img-size-xs"),
					)

