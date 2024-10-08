# Load lists of publications

import os
from datetime import date, timedelta
import logging

from flask import current_app
from flask.cli import AppGroup
import click

from rich.console import Console
from rich.table import Table
from rich import print as rich_print

from .models import db, PeriodicalIssues, Articles, Weeks, Books, VideoCategories, Videos
from .models_whoosh import video_index, illustration_index
from .jworg.publications import PubFinder
from .jworg.meetings import MeetingLoader
from .jworg.videos import VideoLister
from .jworg.epub import EpubLoader
from .utils.babel import gettext as _

logger = logging.getLogger(__name__)

cli_update = AppGroup("update", help="Update lists of publications from JW.ORG")

def init_app(app):
	app.cli.add_command(cli_update)

def basic_callback(message, **kwargs):
	if "{" in message:
		print(message.format(**kwargs))
	else:
		print(message)

#=============================================================================
# Load the weekly schedule from Watchtower Online Library
#=============================================================================

@cli_update.command("meetings", help="Load weekly meeting schedule")
def cmd_update_meetings():
	logging.basicConfig(level=logging.DEBUG)
	update_meetings(basic_callback)

def update_meetings(callback):
	meeting_loader = MeetingLoader(language=current_app.config["PUB_LANGUAGE"])

	current_day = date.today()
	to_fetch = []
	for i in range(8):
		year, week = current_day.isocalendar()[:2]
		week_obj = Weeks.query.filter_by(lang=meeting_loader.language, year=year, week=week).one_or_none()
		if week_obj is None:
			to_fetch.append((year, week))
		current_day += timedelta(weeks=1)

	count = 0
	for year, week in to_fetch:
		callback(_("Fetching week %s %s") % (year, week))
		week_data = meeting_loader.get_week(year, week)
		count += 1
		callback("{total_recv} of {total_expected}", total_recv=count, total_expected=len(to_fetch))
		week_obj = Weeks(
			lang = meeting_loader.language,
			year = year,
			week = week,
			)
		for name, value in week_data.items():
			setattr(week_obj, name, value)
		db.session.add(week_obj)

	db.session.commit()
	callback(_("Meetings loaded"), last_message=True)

#=============================================================================
# Load lists of periodicals (Watchtower, Awake, and Meeting Workbook) into
# the DB. We create an PeriodicalIssues model instance for each issue.
# * The URL of the web version on JW.ORG
# * The filename of the EPUB file in case we want to download it
# We then download the table of contents of each new issue and create an
# Articles model instance for each article.
#=============================================================================

class PeriodicalTable:
	def __init__(self, title):
		self.table = Table(show_header=True, title=title)
		for column in ("Code", "Issue Code", "Issue"):
			self.table.add_column(column)
	def add_row(self, *row):
		self.table.add_row(*row)
	def print(self):
		Console().print(self.table)

@cli_update.command("periodicals", help="Get a list of the issues of indicated periodical  ")
@click.argument("pub_code")
@click.argument("year", required=False)
def cmd_update_periodicals(pub_code, year=None):
	logging.basicConfig(level=logging.DEBUG)
	years = []
	if year == "all":
		years = list(range(2018, date.today().year))
		years.append(None)
	else:
		years.append(year)		# may be None
	for year in years:
		update_periodicals(pub_code, year=year, table=PeriodicalTable("Publication %s for year %s" % (pub_code, year)))

# Using the search parameters provided, get a publications list page from JW.ORG
# and extract the links to the publications listed. Save the information in our DB.
def update_periodicals(pub_code, year=None, table=None):

	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])

	if pub_code == "mwb":
		search_path = "jw-meeting-workbook/"
	else:
		search_path = "magazines/"

	search_query = {
		"pubFilter": pub_code,
		"contentLanguageFilter": pub_finder.language,
		}
	if year is not None:
		search_query["yearFilter"] = str(year)

	# Add these publications to the database or update info if they are already there
	for pub in pub_finder.search(search_path, search_query):
		if not 'issue_code' in pub:		# Midweek Meeting instructions
			continue
		if table is not None:
			table.add_row(pub['code'], pub.get('issue_code'), pub.get('issue'))
		issue = PeriodicalIssues.query.filter_by(lang=pub_finder.language, pub_code=pub['code'], issue_code=pub.get('issue_code')).one_or_none()
		if issue is None:
			issue = PeriodicalIssues(
				lang = pub_finder.language,
				pub_code = pub['code'],
				issue_code = pub['issue_code'],
				)
			db.session.add(issue)
		issue.name = pub['name']
		issue.issue = pub['issue']
		issue.thumbnail = pub['thumbnail']
		issue.href = pub['href']
		issue.formats = pub['formats']

	db.session.commit()

	if table is not None:
		table.print()

@cli_update.command("articles", help="Load article titles from TOC of every periodical in the DB")
def cmd_update_articles():
	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])
	for issue in PeriodicalIssues.query.filter(PeriodicalIssues.filter_by(lang=pub_finder.language).pub_code.in_(("w", "mwb"))):
		print(issue, len(issue.articles))
		if len(issue.articles) == 0:
			for docid, title, href in pub_finder.get_toc(issue.href, docClass_filter=['40','106']):
				issue.articles.append(Articles(
					lang = pub_finder.language,
					docid = docid,
					title = title,
					href = href,
					))
	db.session.commit()

#=============================================================================
# Books and brochures
#=============================================================================

@cli_update.command("books", help="Get a list of books and brochures")
def cmd_update_books():
	logging.basicConfig(level=logging.DEBUG)
	update_books()

def update_books():
	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])
	for pub in pub_finder.search("books/", dict(contentLanguageFilter=pub_finder.language)):
		book = Books.query.filter_by(lang=pub_finder.language, pub_code=pub['code']).one_or_none()
		if book is None:
			book = Books(
				lang = pub_finder.language,
				pub_code = pub['code'],
				)
			db.session.add(book)
		book.name = pub['name']
		book.thumbnail = pub['thumbnail']
		book.href = pub['href']
		book.formats = pub['formats']
	db.session.commit()

#=============================================================================
# Load a list of the videos from JW.ORG
# This assumes the following structure:
# VideoOnDemand
#   -> Category
#      -> Subcategory
#        -> Video
#=============================================================================

@cli_update.command("videos", help="Update list of available videos")
@click.argument("category_key", required=False)
@click.argument("subcategory_key", required=False)
def cmd_update_videos(category_key=None, subcategory_key=None):
	logging.basicConfig(level=logging.DEBUG)
	language = current_app.config["PUB_LANGUAGE"]
	if category_key is None and subcategory_key is None:
		update_videos(language, basic_callback)
	elif category_key is not None and subcategory_key is not None:
		update_video_subcategory(language, category_key, subcategory_key, basic_callback)
	else:
		print("Error: Use no arguments or two")

def update_videos(language, callback):
	# Start with an empty index
	video_index.create()

	# The top-level video categories are in a root container called "VideoOnDemand"
	lister = VideoLister(language=language)
	root = lister.get_category("VideoOnDemand")

	# Iterate over the top levels
	top_level_count = 0
	for category in root.subcategories:
		callback(_("Scanning \"{category_name}\"...").format(category_name=category.name))
		assert len(category.videos) == 0, "Top level categories are not expected to have videos"

		# Each top-level category has two or more subcategories each of which has videos.
		subcategory_count = 0
		for subcategory in category.subcategories:
			if subcategory.key.endswith("Featured"):
				continue
			callback("{total_recv} of {total_expected}",
				total_recv = (top_level_count * 100 + int(subcategory_count * 100 / category.subcategories_count)),
				total_expected = (root.subcategories_count * 100),
				)
			category_db_obj = VideoCategories.query.filter_by(
				lang = lister.language,
				category_key = category.key,
				subcategory_key = subcategory.key,
				).one_or_none()
			if category_db_obj is None:
				category_db_obj = VideoCategories(
					lang = subcategory.language,
					category_key = category.key,
					category_name = category.name,
					subcategory_key = subcategory.key,
					subcategory_name = subcategory.name,
					)
				db.session.add(category_db_obj)
			write_video_category_to_db(category_db_obj, subcategory, callback)
			subcategory_count += 1
		top_level_count += 1

def update_video_subcategory(language, category_key, subcategory_key, callback):
	category_db_obj = VideoCategories.query.filter_by(lang=language, category_key=category_key, subcategory_key=subcategory_key).one()
	lister = VideoLister(language=language)
	category = lister.get_category(category_db_obj.subcategory_key)
	write_video_category_to_db(category_db_obj, category, callback)

def write_video_category_to_db(category_db_obj, category, callback):
	callback(_("Scanning \"{category_name} — {subcategory_name}\"...".format(
		category_name = category_db_obj.category_name,
		subcategory_name = category_db_obj.subcategory_name
		)))
	for video in category.videos:
		video_obj = Videos.query.filter_by(lang=category.language, lank=video.lank).one_or_none()
		if video_obj is None:
			video_obj = Videos(
				lang = category.language,
				lank = video.lank
				)
		video_obj.title = video.title
		video_obj.date = video.date
		video_obj.duration = video.duration
		video_obj.thumbnail = video.thumbnail
		video_obj.href = video.href
		category_db_obj.videos.append(video_obj)
	db.session.commit()
	video_index.add_videos(category_db_obj.videos)
	video_index.commit()

@cli_update.command("video-search", help="Perform a test query on the video index")
@click.argument("q")
def cmd_update_video_query(q):
	for video in video_index.search(q):
		print(video.title)

#=============================================================================
# Index illustrations
#=============================================================================

@cli_update.command("illustrations")
def cmd_update_illustrations():
	illustration_index.create()
	for issue in PeriodicalIssues.query.filter(PeriodicalIssues.epub_filename!=None):
		print(f"issue: {issue.pub_code} {issue.issue_code}")
		index_illustrations(issue.pub_code + "_" + issue.issue_code, issue)
	for book in Books.query.filter(Books.epub_filename!=None):
		print(f"book: {book.pub_code} {book.name}")
		index_illustrations(book.pub_code, book)
	illustration_index.commit()

def index_illustrations(pub_code, publication):
	namespaces = {"xhtml": "http://www.w3.org/1999/xhtml"}
	epub = EpubLoader(os.path.join(current_app.config["MEDIA_CACHEDIR"], publication.epub_filename))
	for article in epub.opf.toc:
		xhtml = epub.load_xml(article.href)
		for figure in xhtml.findall(".//xhtml:figure", namespaces):
			print(" ", figure)
			figcaption = figure.find("./xhtml:figcaption", namespaces)
			if figcaption is not None:
				caption = "".join(figcaption.itertext()).strip().removesuffix("*").rstrip()
				img = figure.find("./xhtml:img", namespaces)
				src = img.attrib["src"]
				alt = img.attrib["alt"]
				illustration_index.add_illustration(pub_code, src, caption, alt)

# For testing
@cli_update.command("illustration-search")
@click.argument("q")
def cmd_update_illustration_search(q):
	for illustration in illustration_index.search(q):
		print(illustration)

