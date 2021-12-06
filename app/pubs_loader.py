import sys, os
import logging
from datetime import date, timedelta
import re
from flask.cli import AppGroup
import click

from app import app
from .models import db, app, Issues, Articles, Videos, Weeks, Books
from .jworg.publications import PubFinder
from .jworg.meetings import MeetingLoader
from .jworg.videos import VideoLister
from .jworg.epub import EpubLoader, namespaces

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

cli_update = AppGroup("update", help="Download lists of publications available on JW.ORG")
app.cli.add_command(cli_update)

cli_download = AppGroup("download", help="Download publications")
app.cli.add_command(cli_download)

LANGUAGE = "ru"

#=============================================================================
# Load the weekly schedule from Watchtower Online Library
#=============================================================================

@cli_update.command("weeks", help="Load weekly meeting schedule")
def cmd_load_weeks():
	logging.basicConfig(level=logging.DEBUG)
	load_weeks()

def load_weeks():
	meeting_loader = MeetingLoader()
	current_day = date.today()
	for i in range(4):
		year, week = current_day.isocalendar()[:2]
		week_obj = Weeks.query.filter_by(year=year).filter_by(week=week).one_or_none()
		if week_obj is None:
			print("Fetching week:", year, week)
			week_data = meeting_loader.get_week(year, week)
			week_obj = Weeks()
			week_obj.year = year
			week_obj.week = week
			for name, value in week_data.items():
				setattr(week_obj, name, value)
			db.session.add(week_obj)
		current_day += timedelta(weeks=1)
	db.session.commit()

#=============================================================================
# Get a list of the current issues of the Meeting Workbook and Watchtower
# (Study Edition) by scraping the appropriate pages of JW.ORG.
# We create an Issues model instance for each issue in which we record:
# * The URL of the web version on JW.ORG
# * The filename of the EPUB file which we download
#=============================================================================

@cli_update.command("study", help="Load current study Watchtowers and Meeting Workbooks")
def cmd_load_study():
	logging.basicConfig(level=logging.DEBUG)
	load_periodicals((
		("magazines/", dict(pubFilter="w", contentLanguageFilter=LANGUAGE)),
		("jw-meeting-workbook/", dict(pubFilter="mwb", contentLanguageFilter=LANGUAGE)),
		))

@cli_update.command("magazines", help="Load Watchtowers and Awakes")
def cmd_load_magazines():
	logging.basicConfig(level=logging.DEBUG)
	# FIXME: get date 
	load_periodicals([("magazines/", dict(yearFilter=year, contentLanguageFilter=LANGUAGE)) for year in range(2018, 2023)])

def load_periodicals(searches):
	pub_finder = PubFinder(cachedir=app.cachedir)
	pubs = []

	for path, filter_dict in searches:
		pubs.extend(pub_finder.search(path, filter_dict))

	# Print a table of what we are adding to the database
	console = Console()
	table = Table(show_header=True)
	for column in ("Code", "Issue Code", "Issue"):
		table.add_column(column)

	# Add these publications to the database or update info if they are already there
	for pub in pubs:
		print(pub)
		if not 'issue_code' in pub:		# Midweek Meeting instructions
			continue
		table.add_row(pub['code'], pub.get('issue_code'), pub.get('issue'))
		issue = Issues.query.filter_by(pub_code=pub['code'], issue_code=pub.get('issue_code')).one_or_none()
		if issue is None:
			issue = Issues()
			db.session.add(issue)
		issue.pub_code = pub['code']
		issue.issue_code = pub['issue_code']
		issue.issue = pub['issue']
		issue.thumbnail = pub['thumbnail']
		issue.href = pub['href']

	console.print(table)

	db.session.commit()

#=============================================================================
# Download the table of contents of each periodical in the database
# and add the articles to the Articles table.
#=============================================================================

@cli_update.command("articles", help="Download the table of contents from each periodical")
def cmd_load_articles():
	logging.basicConfig(level=logging.DEBUG)
	load_articles()

# From web version
def load_articles():
	pub_finder = PubFinder()
	for issue in Issues.query.filter(Issues.pub_code.in_(("w", "mwb"))):
		print(issue, len(issue.articles))
		if len(issue.articles) == 0:
			for docid, title, href in pub_finder.get_toc(issue.href, docClass_filter=['40','106']):
				issue.articles.append(Articles(
					docid = docid,
					title = title,
					href = href,
					))
	db.session.commit()

## From the EPUB files
#def load_articles_epub():
#	for issue in Issues.query:
#		print(issue, len(issue.articles))
#		if len(issue.articles) == 0:
#			epub = EpubLoader(os.path.join(app.cachedir, issue.epub_filename))
#			for article in epub.opf.toc:
#				print(article.title, article.href)
#				doc = epub.load_html(article.href)
#				classes = doc.xpath(".//body")[0].attrib['class']
#				m = re.search(r" docId-(\d+)", classes)
#				if m:
#					issue.articles.append(Articles(
#						docid = int(m.group(1)),
#						title = article.title,
#						epub_href = article.href,
#						))
#	db.session.commit()

#=============================================================================
# Books and brocures
#=============================================================================

@cli_update.command("books", help="Get a list of books and brocures")
def cmd_load_books():
	logging.basicConfig(level=logging.DEBUG)
	load_books()

def load_books():
	pub_finder = PubFinder(cachedir=app.cachedir)
	pubs = pub_finder.search("books/", dict(contentLanguageFilter=LANGUAGE))
	for pub in pubs:
		print(pub)
		book = Books.query.filter_by(pub_code=pub['code']).one_or_none()
		if book is None:
			book = Books()
			db.session.add(book)
		book.name = pub['name']
		book.pub_code = pub['code']
		book.thumbnail = pub['thumbnail']
		book.href = pub['href']
	db.session.commit()

#=============================================================================
# Load a list of the videos from JW.ORG
# This assumes the following structure:
# VideoOnDemand
#   -> Category
#      -> Subcategory
#        -> Video 
#=============================================================================

@cli_update.command("videos", help="Get list of all available videos")
def cmd_update_videos():
	logging.basicConfig(level=logging.DEBUG)
	load_videos()

def load_videos():
	video_lister = VideoLister()
	for category in video_lister.get_category("VideoOnDemand").subcategories:
		print("Category:", category.name)
		assert len(category.videos) == 0
		for subcategory in category.subcategories:
			print("  Subcategory:", subcategory.name)
			for video in subcategory.videos:
				print("    Video:", video.name)
				video_obj = Videos.query.filter_by(lank=video.lank).one_or_none()
				if video_obj is None:
					video_obj = Videos()
					db.session.add(video_obj)
				video_obj.lank = video.lank
				video_obj.name = video.name
				video_obj.category_key = category.key
				video_obj.category_name = category.name
				video_obj.subcategory_key = subcategory.key
				video_obj.subcategory_name = subcategory.name
				video_obj.href = video.href
				video_obj.thumbnail = video.thumbnail
	db.session.commit()

#=============================================================================
#
#=============================================================================

@cli_download.command("book", help="Download EPUB version of a book or brocure")
@click.argument("pub_code")
def cmd_download_book(pub_code):
	book = Books.query.filter_by(pub_code=pub_code).one()
	pub_finder = PubFinder(cachedir=app.cachedir)
	epub_url = pub_finder.get_epub_url(pub_code)
	book.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

@cli_download.command("issue", help="Download EPUB version of a periodical issue")
@click.argument("pub_code")
@click.argument("issue_code")
def cmd_download_issue(pub_code, issue_code):
	issue = Issues.query.filter_by(pub_code=pub_code).filter_by(issue_code=issue_code).one()
	pub_finder = PubFinder(cachedir=app.cachedir)
	epub_url = pub_finder.get_epub_url(pub_code, issue_code)
	issue.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

