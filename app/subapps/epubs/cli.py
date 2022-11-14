import os
from flask.cli import AppGroup
import click

from ... import app
from ...models import db, app, PeriodicalIssues, Books
from ...jworg.publications import PubFinder
from ...jworg.epub import EpubLoader, namespaces

cli_epubs = AppGroup("epubs", help="Download publications into the ePub viewer")
app.cli.add_command(cli_epubs)

@cli_epubs.command("download", help="Download ePub version of a book or brochure")
@click.argument("pub_code")
def cmd_epubs_download_book(pub_code):
	pub_finder = PubFinder(cachedir=app.cachedir)
	if "-" in pub_code:
		pub_code, issue_code = pub_code.split("-",1)
		item = PeriodicalIssues.query.filter_by(pub_code=pub_code).filter_by(issue_code=issue_code).one()
		epub_url = pub_finder.get_epub_url(pub_code, issue_code)
	else:
		item = Books.query.filter_by(pub_code=pub_code).one()
		epub_url = pub_finder.get_epub_url(pub_code)
	item.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

