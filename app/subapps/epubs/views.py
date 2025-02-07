# Views for loading media from JW.ORG into OBS

from flask import current_app, Blueprint, render_template, request, Response, redirect, abort
import os
from collections import defaultdict
import logging

from ...models import db, PeriodicalIssues, Books
from ...models_whoosh import illustration_index
from ...utils.background import progress_callback
from ...jworg.publications import PubFinder
from ...jworg.epub import EpubLoader
from ...cli_jworg import update_periodicals, update_books

logger = logging.getLogger(__name__)

blueprint = Blueprint("epubs", __name__, template_folder="templates", static_folder="static")
blueprint.display_name = "Epub Reader"
blueprint.blurb = "Download and display ePub files from JW.ORG"

lang = current_app.config["PUB_LANGUAGE"]

@blueprint.route("/")
def epub_index():
	periodicals = defaultdict(list)
	for periodical in PeriodicalIssues.query.filter_by(lang=lang).order_by(PeriodicalIssues.pub_code, PeriodicalIssues.issue_code):
		periodicals[periodical.name].append(periodical)
	return render_template(
		"epubs/index.html",
		periodicals = (
			("w", "Watchtower Study Edition",
				PeriodicalIssues.query.filter_by(lang=lang).filter_by(pub_code="w").order_by(PeriodicalIssues.issue_code),
				),
			("wp", "Watchtower Public Edition",
				PeriodicalIssues.query.filter_by(lang=lang).filter_by(pub_code="wp").order_by(PeriodicalIssues.issue_code),
				),
			("g", "Awake!",
				PeriodicalIssues.query.filter_by(lang=lang).filter_by(pub_code="g").order_by(PeriodicalIssues.issue_code),
				),
			("mwb", "Meeting Workbook",
				PeriodicalIssues.query.filter_by(lang=lang).filter_by(pub_code="mwb").order_by(PeriodicalIssues.issue_code),
				),
			),
		books = Books.query.filter_by(lang=lang).order_by(Books.name),
		)

# User has pressed one of the Load buttons to load a list of publications
@blueprint.route("/load", methods=["POST"])
def epub_load():
	pub_code = request.form.get("pub_code")
	if pub_code in ("w", "wp", "g", "mwb"):
		update_periodicals(pub_code)
	else:
		update_books()
	return redirect(".")

# Search for illustrations
@blueprint.route("/illustrations/")
def search_illustrations():
	q = request.args.get("q")
	print("q:", q)
	if q:
		results = illustration_index.search(q)
	else:
		results = []
	return render_template("epubs/illustrations.html", q = q, results = results)

@blueprint.route("/illustrations/<int:docnum>")
def show_illustration(docnum):
	q = request.args.get("q")
	result = illustration_index.get_document(docnum)
	return render_template("epubs/illustration_viewer.html", q = q, result=result)

# Display the Table of Contents from an Epub
@blueprint.route("/<pub_code>/")
def epub_toc(pub_code):
	epub = open_epub(pub_code)
	if epub is None:
		return render_template("epubs/error.html",
			title = pub_code,
			error = f"Publication {pub_code} is not available as an EPUB",
			)

	# Jump to chapter identified by ID
	id = request.args.get("id")
	if id is not None:
		for item in epub.opf.toc:
			if item.id == id:
				return redirect(item.href)

	return render_template("epubs/toc.html", epub=epub)

# Display an Epub page in an <iframe>
@blueprint.route("/<pub_code>/viewer/<path:path>")
def epub_viewer(pub_code, path):
	epub = open_epub(pub_code)
	if epub is None:
		abort(404)
	return render_template("epubs/viewer.html", epub=epub, path="../" + path)

# Open an epub identified by publication code.
# Download it first if it is not downloaded already.
def open_epub(pub_code):
	if "_" in pub_code:
		pub_code, issue_code = pub_code.split("_",1)
		pub = PeriodicalIssues.query.filter_by(lang=lang, pub_code=pub_code).filter_by(issue_code=issue_code).one_or_none()
	else:
		issue_code = None
		pub = Books.query.filter_by(lang=lang, pub_code=pub_code).one_or_none()
	if pub is None:
		logger.error("Publication %s not known", pub_code)
		abort(404)
	if pub.epub_filename is None:
		pub_finder = PubFinder(
			language = lang,
			cachedir = current_app.config["MEDIA_CACHEDIR"],
			)
		epub_url = pub_finder.get_epub_url(pub_code, issue_code)
		if epub_url is None:
			logger.error("Failed to get EPUB URL")
			return None
		progress_callback("Downloading %s" % epub_url)
		epub_filename = pub_finder.download_media(epub_url, callback=progress_callback)
		pub.epub_filename = os.path.basename(epub_filename)
		db.session.commit()
	return EpubLoader(os.path.join(current_app.config["MEDIA_CACHEDIR"], pub.epub_filename))

# Fetch a file from an Epub (used for images)
@blueprint.route("/<pub_code>/<path:path>")
def epub_file(pub_code, path):
	epub = open_epub(pub_code)
	if epub is None:
		abort(404)

	item = epub.opf.manifest_by_href.get(path)
	if item is None:
		abort(404)

	# This may be overkill. It supports range requests
	file_handle, content_length = epub.open(item.href)
	response = Response(file_handle, mimetype=item.mimetype)
	response.make_conditional(request, complete_length = content_length)
	return response

## CSS rules to append to /css/epubs.css
## Epub content is in XHTML format, so the tag names must be in lower case.
#viewer_css_override = """
#body {
#	margin: 0 .5em;
#	}
#"""
#
## Epub stylesheet
#@blueprint.route("/<pub_code>/css/epubs.css")
#def epub_css(pub_code):
#	epub = open_epub(pub_code)
#	if epub is None:
#		abort(404)
#
#	item = epub.opf.manifest_by_href.get("css/epubs.css")
#	if item is None:
#		abort(404)
#
#	file_handle, content_length = epub.open(item.href)
#	css_text = file_handle.read() + viewer_css_override.encode("utf-8")
#
#	return Response(css_text, mimetype=item.mimetype)
