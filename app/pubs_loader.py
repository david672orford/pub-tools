import sys, os
import logging
from datetime import date, timedelta
import re
from flask.cli import AppGroup

from app import app
from .models import db, app, Issues, Articles, Videos, Weeks, Books
from .jworg.publications import PubFinder
from .jworg.meetings import MeetingLoader
from .jworg.videos import VideoLister
from .jworg.epub import EpubLoader, namespaces

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

pubs_cli = AppGroup("pubs", help="Download lists of publications on JW.ORG")
app.cli.add_command(pubs_cli)

#=============================================================================
# Load the weekly schedule from Watchtower Online Library
#=============================================================================

@pubs_cli.command("weeks", help="Load weekly meeting schedule")
def cmd_load_weeks():
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

@pubs_cli.command("periodicals", help="Load Watchtowers and Meeting Workbooks")
def cmd_load_periodicals():
	load_periodicals()

def load_periodicals():
	pub_finder = PubFinder(cachedir=app.cachedir)
	pubs = []

	# Current study Watchtowers
	pubs.extend(pub_finder.search("magazines/", dict(pubFilter="w", contentLanguageFilter="ru")))

	# Load Meeting Workbooks
	pubs.extend(pub_finder.search("jw-meeting-workbook/", dict(pubFilter="mwb", contentLanguageFilter="ru")))

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
		issue.href = pub['href']
		epub_url = pub_finder.get_epub_url(pub['code'],pub['issue_code'])
		issue.epub_filename = os.path.basename(pub_finder.download_media(epub_url))

	console.print(table)

	db.session.commit()

# If load_periodicals() got any new issues, download their tables of contents
# from and add the articles to the Articles table.
@pubs_cli.command("articles")
def cmd_load_articles():
	logging.basicConfig(level=logging.DEBUG)
	load_articles_web()
	#load_articles_epub()

# From web version
def load_articles_web():
	pub_finder = PubFinder()
	for issue in Issues.query:
		print(issue, len(issue.articles))
		if len(issue.articles) == 0:
			for docid, title, href in pub_finder.get_toc(issue.href, docClass_filter=['40','106']):
				issue.articles.append(Articles(
					docid = docid,
					title = title,
					href = href,
					))
	db.session.commit()

# From the EPUB files
def load_articles_epub():
	for issue in Issues.query:
		print(issue, len(issue.articles))
		if len(issue.articles) == 0:
			epub = EpubLoader(os.path.join(app.cachedir, issue.filename))
			for article in epub.opf.toc:
				print(article.title, article.href)
				doc = epub.load_html(article.href)
				classes = doc.xpath(".//body")[0].attrib['class']
				m = re.search(r" docId-(\d+)", classes)
				if m:
					issue.articles.append(Articles(
						docid = int(m.group(1)),
						title = article.title,
						epub_href = article.href,
						))
	db.session.commit()

#=============================================================================
#
#=============================================================================

@pubs_cli.command("books")
def cmd_load_books():
	logging.basicConfig(level=logging.DEBUG)
	load_books()

def load_books():
	pub_finder = PubFinder(cachedir=app.cachedir)
	pubs = pub_finder.search("books/", dict(pubFilter="th", contentLanguageFilter="ru"))
	for pub in pubs:
		print(pub)
		book = Books.query.filter_by(pub_code=pub['code']).one_or_none()
		if book is None:
			book = Books()
			db.session.add(book)
		book.name = pub['name']
		book.pub_code = pub['code']
		book.href = pub['href']
		epub_url = pub_finder.get_epub_url(pub['code'])
		book.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

#=============================================================================
# Load a list of the videos from JW.ORG
# This assumes the following structure:
# VideoOnDemand
#   -> Category
#      -> Subcategory
#        -> Video 
#=============================================================================

@pubs_cli.command("videos")
def cmd_load_videos():
	logging.basicConfig(level=logging.DEBUG)
	load_videos()

def load_videos():
	video_lister = VideoLister()
	for category in video_lister.get_category("VideoOnDemand").subcategories:
		print("Category:", category.name)
		assert len(category.videos) == 0
		for subcategory in category.subcategories:
			print("Subcategory:", subcategory.name)
			for video in subcategory.videos:
				print("Video:", video.name)
				video_obj = Videos.query.filter_by(lank=video.lank).one_or_none()
				if video_obj is None:
					video_obj = Videos()
					db.session.add(video_obj)
				video_obj.lank = video.lank
				video_obj.name = video.name
				video_obj.category = category.name
				video_obj.subcategory = subcategory.name
				video_obj.href = video.href
				video_obj.thumbnail = video.thumbnail
	db.session.commit()

#=============================================================================
#
#=============================================================================

@pubs_cli.command("all")
def cmd_load_all():
	logging.basicConfig(level=logging.DEBUG)
	load_weeks()
	load_periodicals()
	load_articles_web()
	#load_articles_epub()
	load_books()
	load_videos()

