from flask import render_template, request, redirect, flash
from datetime import date
from sqlalchemy import or_, and_
from datetime import date
from threading import Thread
from dataclasses import asdict
import logging

from ... import turbo
from ...utils import progress_callback, progress_callback_response, run_thread
from ...models import db, Weeks, MeetingCache
from ...cli_update import update_meetings
from .views import blueprint
from .utils import meeting_loader, obs, ObsError
from ...jworg.meetings import MeetingMedia

logger = logging.getLogger(__name__)

# List upcoming meetings for which we can load media into OBS
@blueprint.route("/meetings/")
def page_meetings():
	weeks = Weeks.query
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))
	return render_template("khplayer/meetings.html", weeks=weeks.all(), top="..")

# Load more weeks
@blueprint.route("/meetings/update", methods=["POST"])
def page_meetings_update():
	update_meetings(callback=progress_callback)
	return redirect(".")

# Download a meeting article, extract the media list, and display it
@blueprint.route("/meetings/<int:docid>/")
def page_meetings_view(docid):
	title = request.args.get("title")
	media = get_meeting_media_cached(docid)
	return render_template("khplayer/meeting_media.html", meeting_title=title, media=media, top="../..")

# Download the media items and create an OBS scene for each.
@blueprint.route("/meetings/<int:docid>/load", methods=['POST'])
def page_meetings_load(docid):

	# If user provided a scene collection name, create a new one of that name.
	collection = request.form.get("collection").strip()
	if collection != "":
		try:
			obs.create_scene_collection(collection)
		except ObsError as e:
			return progress_callback_response("OBS: " + str(e))

		sleep(1)		# Give GUI time to switch (may not be necessary)

		obs.create_camera_scene(current_app.config["PERIPHERALS"]["camera"])
		obs.create_zoom_scene()
		obs.create_split_scene(current_app.config["PERIPHERALS"]["camera"])

	# The media list will already by in the cache. Get it.
	media = get_meeting_media_cached(docid)

	# Download in the background.
	run_thread(lambda: meeting_media_to_obs_scenes(media))

	return progress_callback_response("Loading media for %s..." % request.form.get("title"))

# Wrapper for get_meeting_media() which caches the responses in a DB table
def get_meeting_media_cached(docid):
	# Look for this meeting's media in the DB cache table
	meeting = MeetingCache.query.filter_by(docid=docid).one_or_none()
	if meeting is not None:
		# Deserialize list from JSON back to objects
		media = list(map(lambda item: MeetingMedia(**item), meeting.media))
	else:
		media = get_meeting_media(docid)
		# Serialize list from objects to JSON and store in DB cache table
		meeting = MeetingCache(docid=docid, media=list(map(lambda item: asdict(item), media)))
		db.session.add(meeting)
		db.session.commit()
	return media

# Download the meeting article (from the Watchtower or Workbook) and
# extract a list of the videos and images.
def get_meeting_media(docid):

	# Construct the sharing URL for the meeting article. This will redirect to the article itself.
	url = "https://www.jw.org/finder?wtlocale=U&docid={docid}&srcid=share".format(docid=docid)

	# Use the meeting loader to download the article and scan it for
	# media such as videos and illustrations.
	media = meeting_loader.extract_media(url, callback=progress_callback)

	return media

# Run in a background thread to download the media and add a scene in OBS for each item.
def meeting_media_to_obs_scenes(items):
	for item in items:
		logger.info("Loading scene: %s", repr(item))
	
		# Add a symbol to the front of the scene name to indicate its type.
		if item.pub_code is not None and item.pub_code.startswith("sjj"):
			scene_name = "♫ " + item.title
		elif item.media_type == "video":
			scene_name = "▷ " + item.title
		elif item.media_type == "image":
			scene_name = "□ " + item.title
		else:
			scene_name = item.title
	
		if item.media_type == "web":		# HTML page
			#obs.add_media_scene(scene_name, media_type, media_url)
			pass
		else:						# video or image file
			media_file = meeting_loader.download_media(item.media_url, callback=progress_callback)
			obs.add_media_scene(scene_name, item.media_type, media_file)

