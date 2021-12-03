from .fetcher import Fetcher
from urllib.parse import urlparse, urljoin, parse_qsl, unquote
import re
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Scan a Meeting Workbook week or Watchtower study article and return
# a list of the vidoes and pictures therein.
class MeetingLoader(Fetcher):

	# Get the articles to be studied during a particular week
	def get_week(self, year, week):
		url = self.week_url.format(year=year, week=week)
		html = self.get_html(url)
		today_items = html.find_class("todayItem")
		assert len(today_items) >= 2

		result = {}

		# For the Meeting Workbook we can extract the MEPS docId
		# directly from the todayItem tag.
		mwb_class = today_items[0].attrib['class']
		assert " pub-mwb " in mwb_class
		result['mwb_docid'] = int(re.search(r" docId-(\d+) ", mwb_class).group(1))

		# For the Watchtower article we have to follow the link. It will
		# redirect to a URL which has the MEPS docId at the end.
		watchtower_class = today_items[1].attrib['class']
		assert " pub-w" in watchtower_class
		item_data = today_items[1].find_class('itemData')[0]
		watchtower_href = urljoin(url, item_data.xpath('.//a')[0].attrib['href'])
		response = self.get(watchtower_href, follow_redirects=False)
		result['watchtower_docid'] = response.geturl().split('/')[-1]

		return result

	# Fetch the indicated article from WWW.JW.ORG, parse the HTML, and return
	# the content of the <article> tag which is inside the <main> tag.
	def get_article_html(self, url):
		html = self.get_html(url)
		container = html.xpath(".//main//article")
		assert len(container) == 1		
		return container[0]

	# Fetch the web version of an article, figure out whether it is a Workbook week
	# or a Watchtower study article and invoke the appropriate media extractor function.
	def extract_media(self, url):
		container = self.get_article_html(url)
		logger.info("Article title: %s" % container.xpath(".//h1")[0].text_content().strip())
		m = re.search(r" pub-(\S+) ", container.attrib['class'])
		assert m
		return getattr(self, "extract_media_%s" % m.group(1))(url, container)

	# Extract the media URL's from the web version of an article in the Meeting Workbook
	def extract_media_mwb(self, url, container):
		container = container.xpath(".//div[@class='bodyTxt']")[0]
		scenes = []
		for section in container:
			assert section.tag == "div" and section.attrib['class'] == "section"
			section_id = section.attrib['id']
			h2s = section.xpath(".//h2")
			section_title = h2s[0].text_content() if len(h2s) > 0 else None
			logger.info("Section: id=%s class=%s title=\"%s\"" % (section_id, section.attrib.get("class"), section_title))
			for a in section.xpath(".//a"):
				logger.info(" href: %s %s", unquote(a.attrib['href']), str(a.attrib))
				while True:

					# Meeting Workbook sample presentation video
					# (Other videos occasionally have them too.)
					# Sample <a> tag attributes:
					# data-video="webpubvid://?pub=mwbv&issue=202105&track=1"
					# href="https://www.jw.org/finder?lank=pub-mwbv_202105_1_VIDEO&wtlocale=U"
					if a.attrib.get("data-video") is not None:
						scenes.append((a.text_content(), "video", self.get_video_url(a.attrib['href'])))
						is_a = "video"
						break

					if "jsBibleLink" in a.attrib.get("class","").split(" "):
						is_a = "verse"
						break

					try:
						pub_code = re.match(r"^pub-(\S+)$", a.attrib['class']).group(1)
						docid = re.match(r"^mid(\d+)$", a.attrib['data-page-id']).group(1)
					except AttributeError:
						raise AssertionError("Not as expected: <%s %s>%s" % (a.tag, str(a.attrib), a.text))

					# Songbook
					if pub_code == "sjj":
						song = a.text_content().strip()
						song_number = re.search(r'(\d+)$', song).group(1)
						scenes.append((song, "video", self.get_song_video_url(song_number)))
						is_a = "song"
						break

					# Counsel points
					if pub_code == "th":
						text = a.text_content().strip()
						#scenes.append((text, "web", urljoin(url, a.attrib['href'])))
						chapter = int(re.search(r"(\d+)$", text).group(1))
						scenes.append((text, "web", "http://localhost:5000/epubs/th/?id=chapter%d" % (chapter + 4)))
						is_a = "counsel point"
						break

					# Video from JW Broadcasting?
					# ijwwb -- whiteboard animation
					# ijwpk -- become Jehovah's friend
					if pub_code.startswith("ijw"):
						docid = a.attrib.get('data-page-id')
						break

					# Links to other publications. Omit those in section three because the
					# are just the source material for demonstrations.
					if section_id != "section3":
						article_title = a.text_content().strip()
						article_main = self.get_article_html(urljoin(url, a.attrib['href']))
						scenes.extend(self.extract_illustrations(article_title, article_main))
						is_a = "article"
						break

					is_a = "unknown"
					break

				logger.info(" Item: %s \"%s\" (%s)" % (str(a.attrib.get('class')).strip(), a.text_content().strip(), is_a))
		return scenes

	# Extract the media URL's from the web version of a Watchtower study article.
	def extract_media_w(self, url, container):

		# <a class='pub-sjj' is a song. There should always be two.
		songs = []
		for a in container.xpath(".//a[@class='pub-sjj']"):
			song = a.text_content().strip()
			m = re.search(r'(\d+)$', song)
			assert m
			songs.append((song, "video", self.get_song_video_url(m.group(1))))
		assert len(songs) == 2, songs

		illustrations = self.extract_illustrations("СБ", container)

		return [songs[0]] + illustrations + [songs[1]]

	# Find the illustrations (<figure> tags) from an article or chapter body.
	# This is used for Watchtower articles and the Congregation Bible Study material.
	def extract_illustrations(self, title, container):
		figures = []
		n = 1
		for figure in container.xpath(".//figure"):
			#self.dump_html(figure)
			figcaption = figure.xpath("./figcaption")
			if len(figcaption) > 0:
				figcaption = "%s %s: %s" % (title, n, figcaption[0].text_content().strip())
			else:
				figcaption = "%s %d" % (title, n)
			figures.append((figcaption, "image", figure.find_class("jsRespImg")[0].attrib['data-zoom']))
			n += 1
		#self.dump_json(figures)
		return figures

