from flask.cli import AppGroup
import click

from ... import app
from ...models import db, app, Issues, Books
from ...jworg.publications import PubFinder
from ...jworg.epub import EpubLoader, namespaces

cli_epub = AppGroup("epub", help="Download publications into the ePub viewer")
app.cli.add_command(cli_epub)

@cli_epub.command("download-book", help="Download ePub version of a book or brochure")
@click.argument("pub_code")
def cmd_epub_download_book(pub_code):
	book = Books.query.filter_by(pub_code=pub_code).one()
	pub_finder = PubFinder(cachedir=app.cachedir)
	epub_url = pub_finder.get_epub_url(pub_code)
	book.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

@cli_epub.command("download-issue", help="Download ePub version of a periodical issue")
@click.argument("pub_code")
@click.argument("issue_code")
def cmd_epub_download_issue(pub_code, issue_code):
	issue = Issues.query.filter_by(pub_code=pub_code).filter_by(issue_code=issue_code).one()
	pub_finder = PubFinder(cachedir=app.cachedir)
	epub_url = pub_finder.get_epub_url(pub_code, issue_code)
	issue.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

