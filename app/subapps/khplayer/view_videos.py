from flask import render_template, request, redirect, flash
from collections import defaultdict
import logging

from ...utils import progress_callback, progress_callback_response, run_thread
from ...models import VideoCategories, Videos
from ...cli_update import update_videos
from .views import blueprint
from .utils import meeting_loader, obs, ObsError

logger = logging.getLogger(__name__)

# List all the categories of videos on JW.org.
@blueprint.route("/videos/")
def page_videos():
	categories = defaultdict(list)
	for category in VideoCategories.query.order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[category.category_name].append((category.subcategory_name, category.category_key, category.subcategory_key))					
	return render_template("khplayer/video_categories.html", categories=categories.items(), top="..")

# When Update button is pressed
@blueprint.route("/videos/submit", methods=["POST"])
def page_videos_submit():
	update_videos(callback=progress_callback)
	return redirect(".")

# List all the videos in a category. Clicking on a video loads it into OBS.
@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def page_videos_list(category_key, subcategory_key):
	category = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("khplayer/video_list.html", category=category, top="../../..")

# Download a video and create a scene for it in OBS
@blueprint.route("/videos/<category_key>/<subcategory_key>/submit", methods=["POST"])
def page_videos_category_subcategory_submit(category_key, subcategory_key):
	lank = request.form.get("lank")
	run_thread(lambda: load_video(lank))
	return progress_callback_response("Loading %s..." % request.form.get("title"))

# Download a video (if it is not already cached) and add it to OBS as a scene
def load_video(lank):
	video = Videos.query.filter_by(lank=lank).one()
	progress_callback("Getting video URL...")
	video_metadata = meeting_loader.get_video_metadata(video.href, resolution="480p")
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)
	try:
		obs.add_media_scene(video.name, "video", video_file)
	except ObsError as e:
		progress_callback("OBS: %s" % str(e))	
	else:
		progress_callback("Video loaded.")

