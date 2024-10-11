from flask.cli import AppGroup, current_app
from time import sleep
import os
from rich import print as rich_print

from ...models import db, Books, PeriodicalIssues
from ...jworg.publications import PubFinder

cli_epubs = AppGroup("epubs", help="Epub operations")

@cli_epubs.command("download-all", help="Download the Epub of everything in our DB")
def cmd_epubs_download_all():
	pub_finder = PubFinder(cachedir=current_app.config["MEDIA_CACHEDIR"])
	for issue in PeriodicalIssues.query.filter(PeriodicalIssues.epub_filename==None):
		print(f"issue: {issue.pub_code} {issue.issue_code}")
		epub_url = pub_finder.get_epub_url(issue.pub_code, issue.issue_code)
		download_epub(pub_finder, issue, epub_url)
	for book in Books.query.filter(Books.epub_filename==None).filter(Books.formats.contains("epub")):
		rich_print(f"book: {book.pub_code} [italic]{book.name}[/italic]")
		epub_url = pub_finder.get_epub_url(book.pub_code)
		download_epub(pub_finder, book, epub_url)

def download_epub(pub_finder, pub, epub_url):
	assert epub_url is not None
	epub_filename = pub_finder.download_media(epub_url)
	pub.epub_filename = os.path.basename(epub_filename)
	db.session.commit()
	sleep(10)

