#=============================================================================
# CLI for loading lists of publications and media from JW.ORG
#=============================================================================

import os
from datetime import date, timedelta
from time import sleep
import logging
import json
from dataclasses import asdict
import re

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
from .jworg.hrange import HighlightRange
from .utils.babel import gettext as _

logger = logging.getLogger(__name__)

cli_jworg = AppGroup("jworg", help="Download lists of publications and media from JW.ORG")

def init_app(app):
	app.cli.add_command(cli_jworg)

# Simple callback to print download progress
def basic_callback(message, **kwargs):
	if "{" in message:
		print(message.format(**kwargs))
	else:
		print(message)

def print_query_result_table(result, title):
	table = Table(show_header=True, title=title, show_lines=True)
	columns = result.column_descriptions[0]["type"].__table__.columns.keys()
	for column in columns:
		table.add_column(column)
	for row in result:
		table.add_row(*[str(getattr(row, column)) for column in columns])
	Console().print(table)

def print_dict_result_table(result, title):
	table = Table(show_header=True, title=title, show_lines=True)
	columns = None
	for row in result:
		if columns is None:
			columns = row.keys()
			for column in columns:
				table.add_column(column)
		table.add_row(*[row[column] for column in columns])
	Console().print(table)

#=============================================================================
# Load the weekly schedule from Watchtower Online Library
#=============================================================================

@cli_jworg.command("update-weeks", help="Load weekly meeting materials")
@click.option("-n", default=8)
def cmd_update_weeks(n):
	logging.basicConfig(level=logging.DEBUG)
	update_weeks(basic_callback, n=n)

def update_weeks(callback, n=8):
	meeting_loader = MeetingLoader(language=current_app.config["PUB_LANGUAGE"])

	current_day = date.today()
	to_fetch = []
	for i in range(n):
		year, week = current_day.isocalendar()[:2]
		week_obj = Weeks.query.filter_by(year=year, week=week).one_or_none()
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
			year = year,
			week = week,
			)
		for name, value in week_data.items():
			setattr(week_obj, name, value)
		db.session.add(week_obj)

	db.session.commit()
	callback(_("Weeks loaded"), last_message=True)

@cli_jworg.command("show-weeks", help="List weekly meeting materials in DB")
def cmd_show_weeks():
	print_query_result_table(Weeks.query, "Weekly Meeting Materials")

#=============================================================================
# Media Extraction Tests
#=============================================================================

@cli_jworg.command("get-meeting-media", help="Scrape a meeting article to get the media")
@click.argument("docid")
def cmd_get_meeting_media(docid):
	meeting_loader = MeetingLoader(language=current_app.config["PUB_LANGUAGE"], debuglevel=0)
	url = meeting_loader.meeting_url(docid)
	media = meeting_loader.extract_media(url, callback=basic_callback)
	print_dict_result_table(map(lambda item: asdict(item), media), "Meeting Media")

@cli_jworg.command("get-article-media", help="Scrape an article to get the media")
@click.argument("url")
def cmd_get_article(url):
	meeting_loader = MeetingLoader(language=current_app.config["PUB_LANGUAGE"], debuglevel=0)
	root = meeting_loader.get_article(url).article_tag
	meeting_loader.dump_html(root, "article.html")

	hrange = HighlightRange(root)
	hrange.print()

	return

	media_items = []
	for figure in hrange.figures:
		figure_tags = figure.el.xpath(".//figure")
		assert len(figure_tags) == 1
		for item in meeting_loader.get_figure_items(figure_tags[0], url, {"image", "video", "song", "web"}):
			media_items.append({
				"figure": figure.el.attrib["id"],
				"paragraph": str(figure.pnum),
				"media_type": item.media_type,
				"title": item.title,
				"media_url": item.media_url,
				"thumbnail_url": item.thumbnail_url,
				})
	print_dict_result_table(media_items, "Media Items")

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

@cli_jworg.command("update-periodicals", help="Load the list of the issues of indicated periodical")
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
		if pub.issue_code is None:		# Midweek Meeting instructions
			continue
		if table is not None:
			table.add_row(pub.code, pub.issue_code, pub.issue)
		issue = PeriodicalIssues.query.filter_by(lang=pub_finder.language, pub_code=pub.code, issue_code=pub.issue_code).one_or_none()
		if issue is None:
			issue = PeriodicalIssues(
				lang = pub_finder.language,
				pub_code = pub.code,
				issue_code = pub.issue_code,
				)
			db.session.add(issue)
		issue.name = pub.name
		issue.issue = pub.issue
		issue.thumbnail = pub.thumbnail
		issue.href = pub.href
		issue.formats = pub.formats

	db.session.commit()

	if table is not None:
		table.print()

@cli_jworg.command("show-periodicals", help="List periodicals in DB")
def cmd_show_periodicals():
	print_query_result_table(PeriodicalIssues.query, "Periodical Issues")

@cli_jworg.command("update-articles", help="Load article titles from TOC of every periodical in the DB")
def cmd_update_articles():
	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])
	for issue in PeriodicalIssues.query.filter(PeriodicalIssues.lang==pub_finder.language).filter(PeriodicalIssues.pub_code.in_(("w", "g", "mwb"))):
		print(issue, len(issue.articles))
		if len(issue.articles) == 0:
			for docid, title, href in pub_finder.get_toc(issue.href, docClass_filter=["40","106"]):
				issue.articles.append(Articles(
					lang = pub_finder.language,
					docid = docid,
					title = title,
					href = href,
					))
	db.session.commit()

@cli_jworg.command("show-articles", help="List articles in DB")
def cmd_show_articles():
	articles = []
	for article in Articles.query:
		articles.append(dict(
			id = str(article.id),
			lang = article.lang,
			periodical_name = article.issue.name,
			periodical_issue = article.issue.issue,
			article_title = article.title,
			docid = article.docid,
			))

	print_dict_result_table(articles, "Articles")

#=============================================================================
# Books and brochures
#=============================================================================

@cli_jworg.command("update-books", help="Load list of books and brochures")
def cmd_update_books():
	logging.basicConfig(level=logging.DEBUG)
	update_books()

def update_books():
	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])
	for pub in pub_finder.search("books/", dict(contentLanguageFilter=pub_finder.language)):
		book = Books.query.filter_by(lang=pub_finder.language, pub_code=pub.code).one_or_none()
		if book is None:
			book = Books(
				lang = pub_finder.language,
				pub_code = pub.code,
				)
			db.session.add(book)
		book.name = pub.name
		book.thumbnail = pub.thumbnail
		book.href = pub.href
		book.formats = pub.formats
	db.session.commit()

@cli_jworg.command("show-books", help="List books in DB")
def cmd_show_books():
	print_query_result_table(Books.query, "Books")

#=============================================================================
# Load a list of the videos from JW.ORG
# This assumes the following structure:
# VideoOnDemand
#   -> Category
#      -> Subcategory
#        -> Video
#=============================================================================

@cli_jworg.command("update-videos", help="Update list of available videos")
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

# Update all video categories
def update_videos(language, callback):

	# Start with an empty index
	video_index.create()

	# The top-level video categories are in a root container called "VideoOnDemand"
	lister = VideoLister(language=language)
	root = lister.get_category("VideoOnDemand")

	# Iterate over the top levels
	top_level_count = 0
	for category in root.subcategories:
		if category.key == "VODAudioDescriptions":
			continue	# Omit
		callback(_("Scanning \"{category_name}\"...").format(category_name=category.name))
		assert len(category.videos) == 0, "Top level categories are not expected to have videos"

		# Each top-level category has two or more subcategories each of which has videos.
		subcategory_count = 0
		for subcategory in category.subcategories:
			if subcategory.key.endswith("Featured"):
				continue	# Omit
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
	lister = VideoLister(language=language)
	subcategory = lister.get_category(subcategory_key)
	category_db_obj = VideoCategories.query.filter_by(
		lang = language,
		category_key = category_key,
		subcategory_key = subcategory_key,
		).one_or_none()
	if category_db_obj is None:
		category = lister.get_category(category_key)
		category_db_obj = VideoCategories(
			lang = subcategory.language,
			category_key = category.key,
			category_name = category.name,
			subcategory_key = subcategory.key,
			subcategory_name = subcategory.name,
			)
		db.session.add(category_db_obj)
	write_video_category_to_db(category_db_obj, subcategory, callback)

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

@cli_jworg.command("show-videos", help="List videos in DB")
def cmd_show_videos():
	print_query_result_table(Videos.query, "Videos")

@cli_jworg.command("search-videos", help="Perform a test query on the video index")
@click.argument("q")
def cmd_search_videos(q):
	result, suggestion = video_index.search(q)
	table = Table(show_header=True, title="Matching Videos", show_lines=True)
	columns = Videos.__table__.columns.keys()
	for column in columns:
		table.add_column(column)
	for category, video in result:
		#print(category, video)
		table.add_row(*[str(getattr(video, column)) for column in columns])
	Console().print(table)
	print("Suggestion:", suggestion)

#=============================================================================
# Download Epubs
#=============================================================================

@cli_jworg.command("download-epubs", help="Download the Epub of the indicated publication")
@click.argument("pub_code")
def cmd_download_epubs(pub_code):
	pub_finder = PubFinder(
			language = current_app.config["PUB_LANGUAGE"],
			cachedir = current_app.config["MEDIA_CACHEDIR"],
			)
	if pub_code in ("w", "wp", "g", "mwb"):
		for issue in PeriodicalIssues.query.filter_by(pub_code=pub_code).filter(PeriodicalIssues.epub_filename==None):
			print(f"issue: {issue.pub_code} {issue.issue_code}")
			epub_url = pub_finder.get_epub_url(issue.pub_code, issue.issue_code)
			download_epub(pub_finder, issue, epub_url)
	else:
		for book in Books.query.filter_by(pub_code=pub_code).filter(Books.epub_filename==None).filter(Books.formats.contains("epub")):
			rich_print(f"book: {book.pub_code} [italic]{book.name}[/italic]")
			epub_url = pub_finder.get_epub_url(book.pub_code)
			download_epub(pub_finder, book, epub_url)

def download_epub(pub_finder, pub, epub_url):
	assert epub_url is not None
	epub_filename = pub_finder.download_media(epub_url, callback=basic_callback)
	pub.epub_filename = os.path.basename(epub_filename)
	db.session.commit()
	sleep(10)

#=============================================================================
# Index illustrations
#=============================================================================

@cli_jworg.command("index-illustrations", help="Index illustrations in periodicals and books")
def cmd_index_illustrations():
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
@cli_jworg.command("search-illustrations", help="Search illustration captions")
@click.argument("q")
def cmd_search_illustrations(q):
	illustrations = illustration_index.search(q)
	print_dict_result_table(illustrations, "Illustration Search Results")

