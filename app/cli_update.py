# Load lists of publications

from flask import current_app
import sys, os, re, json
from datetime import date, timedelta
from flask.cli import AppGroup
import click
import logging

from .models import db, PeriodicalIssues, Articles, Weeks, Books, VideoCategories, Videos
from .models_whoosh import update_video_index, video_search
from .jworg.publications import PubFinder
from .jworg.meetings import MeetingLoader
from .jworg.videos import VideoLister
from .utils.babel import gettext as _

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

cli_update = AppGroup("update", help="Update lists of publications from JW.ORG")

def init_app(app):
	app.cli.add_command(cli_update)

def default_callback(message, last_message=False):
	print(message)

#=============================================================================
# Load the weekly schedule from Watchtower Online Library
#=============================================================================

@cli_update.command("meetings", help="Load weekly meeting schedule")
def cmd_update_meetings():
	logging.basicConfig(level=logging.DEBUG)
	update_meetings()

def update_meetings(callback=default_callback):
	meeting_loader = MeetingLoader()
	current_day = date.today()
	for i in range(8):
		year, week = current_day.isocalendar()[:2]
		week_obj = Weeks.query.filter_by(year=year).filter_by(week=week).one_or_none()
		if week_obj is None:
			callback(_("Fetching week %s %s") % (year, week))
			week_data = meeting_loader.get_week(year, week)
			week_obj = Weeks()
			week_obj.year = year
			week_obj.week = week
			for name, value in week_data.items():
				setattr(week_obj, name, value)
			db.session.add(week_obj)
		current_day += timedelta(weeks=1)
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

	if pub_code == "mwb":
		search_path = "jw-meeting-workbook/"
	else:
		search_path = "magazines/"

	search_query = {
		"pubFilter": pub_code,
		"contentLanguageFilter": current_app.config["PUB_LANGUAGE"],
		}

	if year is not None:
		search_query["yearFilter"] = str(year)

	pubs = PubFinder(cachedir=current_app.config["CACHEDIR"], debuglevel=0).search(search_path, search_query)

	# Add these publications to the database or update info if they are already there
	for pub in pubs:
		if not 'issue_code' in pub:		# Midweek Meeting instructions
			continue
		if table is not None:
			table.add_row(pub['code'], pub.get('issue_code'), pub.get('issue'))
		issue = PeriodicalIssues.query.filter_by(pub_code=pub['code'], issue_code=pub.get('issue_code')).one_or_none()
		if issue is None:
			issue = PeriodicalIssues()
			db.session.add(issue)
		issue.name = pub['name']
		issue.pub_code = pub['code']
		issue.issue_code = pub['issue_code']
		issue.issue = pub['issue']
		issue.thumbnail = pub['thumbnail']
		issue.href = pub['href']
		issue.formats = pub['formats']

	db.session.commit()

	if table is not None:
		table.print()

@cli_update.command("articles", help="Load article titles from TOC of every periodical in the DB")
def cmd_update_articles():
	pub_finder = PubFinder()
	for issue in PeriodicalIssues.query.filter(PeriodicalIssues.pub_code.in_(("w", "mwb"))):
		print(issue, len(issue.articles))
		if len(issue.articles) == 0:
			for docid, title, href in pub_finder.get_toc(issue.href, docClass_filter=['40','106']):
				issue.articles.append(Articles(
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
	pub_finder = PubFinder(cachedir=current_app.config["CACHEDIR"])
	language = current_app.config["PUB_LANGUAGE"]
	pubs = pub_finder.search("books/", dict(contentLanguageFilter=language))
	for pub in pubs:
		book = Books.query.filter_by(pub_code=pub['code']).one_or_none()
		if book is None:
			book = Books()
			db.session.add(book)
		book.name = pub['name']
		book.pub_code = pub['code']
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
	if category_key is not None and subcategory_key is not None:
		update_video_subcategory(category_key, subcategory_key)
	else:
		update_videos()
	db.session.commit()
	update_video_index()

def update_videos(callback=default_callback):
	for category in VideoLister().get_category("VideoOnDemand").subcategories:
		callback("%s" % category.name)
		assert len(category.videos) == 0
		for subcategory in category.subcategories:
			if subcategory.key.endswith("Featured"):
				continue
			update_video_subcategory(category.key, category.subcategory_key, callback=callback)

def update_video_subcategory(category_key, subcategory_key, callback=default_callback, flash=False):
	category_db_obj = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	if category_db_obj is None:
		category_db_obj = VideoCategories(
			category_key = category.key,
			category_name = category.name,
			subcategory_key = subcategory.key,
			subcategory_name = subcategory.name,
			)
		db.session.add(category_db_obj)

	callback(_("Scanning {category_name} — {subcategory_name}...".format(category_name=category_db_obj.category_name, subcategory_name=category_db_obj.subcategory_name)))

	for video in VideoLister().get_category(subcategory_key).videos:
		video_obj = Videos.query.filter_by(lank=video.lank).one_or_none()
		if video_obj is None:
			video_obj = Videos()
		video_obj.lank = video.lank
		video_obj.name = video.name
		video_obj.date = video.date
		video_obj.thumbnail = video.thumbnail
		video_obj.href = video.href
		category_db_obj.videos.append(video_obj)

@cli_update.command("video-index", help="Update search index of available videos")
def cmd_update_video_index():
	update_video_index()

@cli_update.command("video-search", help="Perform a test query on the video index")
@click.argument("q")
def cmd_update_video_query(q):
	for video in video_search(q):
		print(video.name)

