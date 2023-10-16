from flask import render_template, request, redirect, flash
from collections import defaultdict
import logging

from ...utils import progress_callback, progress_response, run_thread
from ...models import VideoCategories, Videos
from ...cli_update import update_videos, update_video_subcategory
from ...babel import gettext as _
from .views import blueprint, menu
from .utils import load_video

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
@blueprint.route("/videos/search", methods=["POST"])
def page_videos_search():
	flash("Search not yet implemented")
	return redirect(".")

# When Update button is pressed
@blueprint.route("/videos/update-all", methods=["POST"])
def page_videos_update_all():
	update_videos(callback=progress_callback)
	return redirect(".")

# List all the videos in a category. Clicking on a video loads it into OBS.
@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def page_videos_list(category_key, subcategory_key):
	subcategory = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("khplayer/videos_subcategory.html", subcategory=subcategory, top="../../..")

# Update the videos in a category
@blueprint.route("/videos/<category_key>/<subcategory_key>/update", methods=["POST"])
def page_videos_category_subcategory_update(category_key, subcategory_key):
	update_video_subcategory(category_key, subcategory_key, callback=progress_callback)
	return redirect(".")

# Download a video and create a scene for it in OBS
@blueprint.route("/videos/<category_key>/<subcategory_key>/download", methods=["POST"])
def page_videos_category_subcategory_download(category_key, subcategory_key):
	lank = request.form.get("lank")
	run_thread(lambda: load_video(lank))
	return progress_response(_("Downloading %s...") % request.form.get("title"))

