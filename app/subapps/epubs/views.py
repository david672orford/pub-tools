# Views for loading media from JW.ORG into OBS

from flask import Blueprint, render_template, request, Response, redirect, abort
import os
from collections import defaultdict
import logging

from ...models import Issues, Books
from ... import app
from ...jworg.epub import EpubLoader

logger = logging.getLogger(__name__)

blueprint = Blueprint('epubs', __name__, template_folder="templates", static_folder="static")
blueprint.display_name = 'Epubs'

@blueprint.route("/")
def epub_index():
	return render_template(
		"epubs/index.html",
		periodicals=Issues.query.order_by(Issues.pub_code, Issues.issue_code),
		books=Books.query.order_by(Books.name),
		)

@blueprint.route("/<pub_code>/")
def epub_toc(pub_code):
	epub = open_epub(pub_code)
	id = request.args.get("id")
	if id is not None:
		for item in epub.opf.toc:
			if item.id == id:
				return redirect(item.href)
	return render_template("epubs/toc.html", epub=epub)

@blueprint.route("/<pub_code>/<path:path>")
def epub_file(pub_code, path):
	epub = open_epub(pub_code)
	item = epub.opf.manifest_by_href.get(path)
	if item is None:
		abort(404)

	file_handle, content_length = epub.open(item.href)
	response = Response(file_handle, mimetype=item.mimetype)
	response.make_conditional(request, complete_length = content_length)
	return response

def open_epub(pub_code):
	if "-" in pub_code:
		pub_code, issue_code = pub_code.split("-",1)
		pub = Issues.query.filter_by(pub_code=pub_code).filter_by(issue_code=issue_code).one_or_none()
	else:
		pub = Books.query.filter_by(pub_code=pub_code).one_or_none()
	if pub is None or pub.epub_filename is None:
		abort(404)
	return EpubLoader(os.path.join(app.cachedir, pub.epub_filename))
