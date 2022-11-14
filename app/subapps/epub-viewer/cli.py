from flask.cli import AppGroup
import click

from ... import app
from ...models import db, app, PeriodicalIssues, Books
from ...jworg.publications import PubFinder
from ...jworg.epub import EpubLoader, namespaces

cli_epub = AppGroup("epub", help="Download publications into the ePub viewer")
app.cli.add_command(cli_epub)

@cli_epub.command("download", help="Download ePub version of a book or brochure")
@click.argument("pub_code", nargs=1)
@click.argument("issues", nargs=-1)
def cmd_epub_download_book(pub_code, issues):
	pub_finder = PubFinder(cachedir=app.cachedir)
	if len(issue) == 0:
		item = Books.query.filter_by(pub_code=pub_code).one()
		epub_url = pub_finder.get_epub_url(pub_code)
		item.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	else:
		for issue in issues:
			item = PeriodicalIssues.query.filter_by(pub_code=pub_code).filter_by(issue_code=issue_code).one()
			epub_url = pub_finder.get_epub_url(pub_code, issue_code)
			item.epub_filename = os.path.basename(pub_finder.download_media(epub_url))
	db.session.commit()

