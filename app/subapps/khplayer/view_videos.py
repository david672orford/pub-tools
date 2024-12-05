from flask import current_app, render_template, request, redirect, abort
from collections import defaultdict
from urllib.parse import urlencode
from markupsafe import escape
from time import sleep
import logging

from ...models import db, VideoCategories, Videos
from ...models_whoosh import video_index
from ...utils.background import progress_callback, progress_response, run_thread
from ...utils.babel import gettext as _
from .utils.scenes import load_video_url
from .utils.controllers import meeting_loader
from ...cli_jworg import update_videos, update_video_subcategory
from . import menu
from .views import blueprint

logger = logging.getLogger(__name__)

menu.append((_("Videos"), "/videos/"))

# List all the categories of videos on JW.org.
@blueprint.route("/videos/")
def page_videos():
	categories = defaultdict(list)
	for category in VideoCategories.query.filter_by(lang=meeting_loader.language).order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[(category.category_key, category.category_name)].append(category)
	return render_template("khplayer/videos.html", categories=categories.items(), top="..")

# When Search button pressed
@blueprint.route("/videos/search")
def page_videos_search():
	q = request.args.get("q")
	if q is None:
		return redirect(".")
	search_results, search_suggestion = video_index.search(q)
	if search_suggestion:
		search_suggestion = '<a href="search?%s">%s</a>' % (urlencode(dict(q=search_suggestion)), escape(search_suggestion))
	return render_template(
		"khplayer/videos_search.html",
		q = q,
		search_results = search_results,
		search_suggestion = search_suggestion,
		top = ".."
		)

# List all the videos in a category. Clicking on a video loads it into OBS.
@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def page_videos_list(category_key, subcategory_key):
	category = VideoCategories.query.filter_by(
		lang = meeting_loader.language,
		category_key = category_key,
		subcategory_key = subcategory_key,
		).one_or_none()
	if category is None:
		abort(404)
	return render_template("khplayer/videos_category.html", category=category, top="../../..")

# Download a video and create a scene for it in OBS
@blueprint.route("/videos/download", methods=["POST"])
def page_videos_download():
	video = Videos.query.filter_by(id=request.form.get("id")).one()
	run_thread(lambda: load_video_url(video.title, video.href, thumbnail_url=video.thumbnail))
	return progress_response(None)

# When Update button is pressed on top index page
@blueprint.route("/videos/update-all", methods=["POST"])
def page_videos_update_all():
	progress_callback(_("Updating video list..."), cssclass="heading")
	update_videos(meeting_loader.language, callback=progress_callback)
	progress_callback(_("✔ Video list updated."), cssclass="success", close=True)
	sleep(2)
	return redirect(".")

# When Update button is pressed on a category page
@blueprint.route("/videos/<category_key>/<subcategory_key>/update", methods=["POST"])
def page_videos_category_subcategory_update(category_key, subcategory_key):
	progress_callback(_("Updating video list..."), cssclass="heading")
	update_video_subcategory(meeting_loader.language, category_key, subcategory_key, callback=progress_callback)
	progress_callback(_("✔ Video list updated."), cssclass="success", close=True)
	sleep(1)
	return redirect(".")
