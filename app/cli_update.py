# Load lists of publications

import sys, os
import logging
from datetime import date, timedelta
import re
from flask.cli import AppGroup
import click
import json

from app import app
from .models import db, app, Issues, Articles, Weeks, Books, VideoCategories, Videos
from .jworg.publications import PubFinder
from .jworg.meetings import MeetingLoader
from .jworg.videos import VideoLister

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

cli_update = AppGroup("update", help="Update lists of publications from JW.ORG")
app.cli.add_command(cli_update)

LANGUAGE = "ru"

#=============================================================================
# Load the weekly schedule from Watchtower Online Library
#=============================================================================

@cli_update.command("meetings", help="Load weekly meeting schedule")
def cmd_load_meetings():
	logging.basicConfig(level=logging.DEBUG)
	load_meetings()

def load_meetings():
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
# Load lists of periodicals (Watchtower, Awake, and Meeting Workbook) into
# the DB. We create an Issues model instance for each issue.
# * The URL of the web version on JW.ORG
# * The filename of the EPUB file in case we want to download it
# We then download the table of contents of each new issue and create an
# Articles model instance for each article.
#=============================================================================

@cli_update.command("study-pubs", help="Add current study Watchtowers and Meeting Workbooks to DB")
def cmd_update_study():
	logging.basicConfig(level=logging.DEBUG)
	update_periodicals((
		("magazines/", dict(pubFilter="w", contentLanguageFilter=LANGUAGE)),
		("jw-meeting-workbook/", dict(pubFilter="mwb", contentLanguageFilter=LANGUAGE)),
		))
	update_articles()

@cli_update.command("magazines", help="Add all available Watchtowers and Awakes to DB")
def cmd_update_magazines():
	logging.basicConfig(level=logging.DEBUG)
	end_year = date.today().year
	update_periodicals(
		[("magazines/", dict(yearFilter=year, contentLanguageFilter=LANGUAGE)) for year in range(2018, end_year)]
		+
		[["magazines/", dict(contentLanguage=LANGUAGE)]]
		)
	update_articles()

# Scrape a periodical lists from JW.ORG and add them to the Periodicals
# model in the DB if they are not there already.
def update_periodicals(searches):
	pub_finder = PubFinder(cachedir=app.cachedir, debuglevel=0)
	pubs = []

	print(json.dumps(searches, indent=2))
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
		issue.name = pub['name']
		issue.pub_code = pub['code']
		issue.issue_code = pub['issue_code']
		issue.issue = pub['issue']
		issue.thumbnail = pub['thumbnail']
		issue.href = pub['href']

	console.print(table)

	db.session.commit()

# Download the table of contents of each periodical in the database
# and add the articles to the Articles model in the DB if they are
# not there already.
def update_articles():
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

#=============================================================================
# Books and brochures
#=============================================================================

@cli_update.command("books", help="Get a list of books and brochures")
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

@cli_update.command("videos", help="Update list of all available videos")
def cmd_update_videos():
	logging.basicConfig(level=logging.DEBUG)
	update_videos()

def update_videos():
	for category in VideoLister().get_category("VideoOnDemand").subcategories:
		print("Category:", category.name)
		assert len(category.videos) == 0
		for subcategory in category.subcategories:
			print("  Subcategory:", subcategory.name)
			if subcategory.key.endswith("Featured"):
				continue
			category_obj = VideoCategories.query.filter_by(category_key=category.key).filter_by(subcategory_key=subcategory.key).one_or_none()
			if category_obj is None:
				category_obj = VideoCategories(
					category_key = category.key,
					category_name = category.name,
					subcategory_key = subcategory.key,
					subcategory_name = subcategory.name,
					)
				db.session.add(category_obj)
			for video in subcategory.videos:
				print("    Video:", video.name)
				video_obj = Videos.query.filter_by(lank=video.lank).one_or_none()
				if video_obj is None:
					video_obj = Videos()
				video_obj.lank = video.lank
				video_obj.name = video.name
				video_obj.date = video.date
				video_obj.href = video.href
				video_obj.thumbnail = video.thumbnail
				category_obj.videos.append(video_obj)
	db.session.commit()

