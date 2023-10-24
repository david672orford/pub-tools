from flask import render_template, request, redirect, flash
from collections import defaultdict
from urllib.parse import urlencode
from markupsafe import escape
import logging

from ...models import db, VideoCategories, Videos
from ...utils import progress_callback, progress_response, run_thread
from ...models_whoosh import update_video_index, video_search
from ...cli_update import update_videos, update_video_subcategory
from ...utils.babel import gettext as _
from .views import blueprint, menu
from .utils.scenes import load_video

logger = logging.getLogger(__name__)

menu.append((_("Videos"), "/videos/"))

# List all the categories of videos on JW.org.
@blueprint.route("/videos/")
def page_videos():
	categories = defaultdict(list)
	for category in VideoCategories.query.order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[category.category_name].append((category.subcategory_name, category.category_key, category.subcategory_key))					
	return render_template("khplayer/videos.html", categories=categories.items(), top="..")

# When Search button pressed
@blueprint.route("/videos/search")
def page_videos_search():
	q = request.args.get("q")	
	search_results, search_suggestion = video_search(q)
	if search_suggestion:
		search_suggestion = '<a href="search?%s">%s</a>' % (urlencode(dict(q=search_suggestion)), escape(search_suggestion))
	return render_template(
		"khplayer/videos_search.html",
		q = q,
		search_results = search_results,
		search_suggestion = search_suggestion,
		top = ".."
		)

# When Update button is pressed
@blueprint.route("/videos/update-all", methods=["POST"])
def page_videos_update_all():
	progress_callback(_("Updating video list..."))
	update_videos(callback=progress_callback)
	db.session.commit()
	progress_callback(_("Updating video index..."))
	update_video_index()
	progress_callback(_("Video list updated"))
	return redirect(".")

# List all the videos in a category. Clicking on a video loads it into OBS.
@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def page_videos_list(category_key, subcategory_key):
	category = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("khplayer/videos_category.html", category=category, top="../../..")

# Update the videos in a category
@blueprint.route("/videos/<category_key>/<subcategory_key>/update", methods=["POST"])
def page_videos_category_subcategory_update(category_key, subcategory_key):
	progress_callback(_("Updating video list..."))
	update_video_subcategory(category_key, subcategory_key, callback=progress_callback)
	db.session.commit()
	progress_callback(_("Updating video index..."))
	update_video_index()
	progress_callback(_("Video list updated"))
	return redirect(".")

# Download a video and create a scene for it in OBS
@blueprint.route("/videos/download", methods=["POST"])
def page_videos_download():
	video = Videos.query.filter_by(id=request.form.get("id")).one()
	run_thread(lambda: load_video(video.href))
	return progress_response(_("Downloading %s...") % video.name)

