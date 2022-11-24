from flask import render_template, request, redirect, flash
from collections import defaultdict
import logging

from ... import app, turbo
from ...models import VideoCategories, Videos
from ...cli_update import update_videos
from .views import blueprint
from .utils import meeting_loader, obs_connect, run_thread, make_progress_callback

logger = logging.getLogger(__name__)

# List all the categories of videos on JW.org.
@blueprint.route("/videos/")
def page_videos():
	categories = defaultdict(list)
	for category in VideoCategories.query.order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[category.category_name].append((category.subcategory_name, category.category_key, category.subcategory_key))					
	return render_template("khplayer/video_categories.html", categories=categories.items(), top="..")

@blueprint.route("/videos/submit", methods=["POST"])
def page_videos_submit():
	progress_callback = make_progress_callback()
	update_videos(callback=progress_callback)
	return redirect(".")

# List all the videos in a category. Clicking on a video loads it into OBS.
@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def page_videos_list(category_key, subcategory_key):
	category = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("khplayer/video_list.html", category=category, top="../../..")

@blueprint.route("/videos/<category_key>/<subcategory_key>/submit", methods=["POST"])
def page_videos_category_subcategory_submit(category_key, subcategory_key):
	lank = request.form.get("lank")
	progress_callback = make_progress_callback()
	run_thread(lambda: load_video(lank, progress_callback))
	return redirect(".")

# Download a video (if it is not already cached) and add it to OBS as a scene
def load_video(lank, progress_callback):
	video = Videos.query.filter_by(lank=lank).one()
	logger.info('Load video: "%s" "%s"', video.name, video.href)
	progress_callback("Getting video URL...")
	media_url = meeting_loader.get_video_url(video.href)
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	obs = obs_connect(callback=progress_callback)
	if obs is not None:
		obs.add_scene(video.name, "video", media_file)
		progress_callback("Video loaded.")

