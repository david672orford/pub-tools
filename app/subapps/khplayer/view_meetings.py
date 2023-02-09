from flask import current_app, render_template, request, redirect, flash, stream_with_context
from datetime import date
from time import sleep
from sqlalchemy import or_, and_
from datetime import date
from threading import Thread
from dataclasses import asdict
from markupsafe import escape
import logging

from ... import turbo
from ...utils import progress_callback, progress_callback_response, run_thread
from ...models import db, Weeks, MeetingCache
from ...cli_update import update_meetings
from .views import blueprint
from .utils import meeting_loader, obs, ObsError
from ...jworg.meetings import MeetingMedia
from .cameras import get_camera_dev
from .zoom import find_second_window

logger = logging.getLogger(__name__)

# List upcoming meetings so user can click on the one he wants to load.
@blueprint.route("/meetings/")
def page_meetings():
	weeks = Weeks.query
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))
	return render_template("khplayer/meetings.html", weeks=weeks.all(), top="..")

# User has pressed the "Load More Weeks" button.
@blueprint.route("/meetings/update", methods=["POST"])
def page_meetings_update():
	update_meetings(callback=progress_callback)
	return redirect(".")

# User has clicked on a meeting from the list.
# Download a meeting article, extract the media list, and display it.
@blueprint.route("/meetings/<int:docid>/")
def page_meetings_view(docid):
	title = request.args.get("title")
	return render_template("khplayer/meeting_media.html", meeting_title=title, top="../..")

@blueprint.route("/meetings/<int:docid>/stream")
def page_meetings_view_stream(docid):
	def streamer():
		for item in get_meeting_media_cached(docid):
			data = render_template("khplayer/meeting_media_item.html", item=item)
			yield "data: " + data.replace("\n", " ") + "\n\n"
			sleep(.1)
	response = current_app.response_class(stream_with_context(streamer()), content_type="text/event-stream")
	return response

# Use has pressed the "Download Media and Create Scenes in OBS" button
@blueprint.route("/meetings/<int:docid>/load", methods=['POST'])
def page_meetings_load(docid):

	collection = "KH Player"
	scene_list = []
	try:
		obs.create_scene_collection(collection)
	except ObsError as e:
		if e.code == 601:
			# Scene collection already exists. Empty it.
			for scene in obs.get_scene_list():
				# FIXME: get names from obs module
				if scene['sceneName'] not in ("Stage", "Zoom", "Split Screen"):
					obs.remove_scene(scene['sceneName'])
		else:
			return progress_callback_response("OBS: " + str(e))

	# Give GUI time to switch (may not actually be necessary)
	sleep(1)

	# FIXME: Disabled because we are not deleting these above. Deleting them and 
	#        recreating them was causing problems in OBS because OBS wouldn't
	#        delete the active source.
	#
	# Create the stage and Zoom scenes no matter whether the camera
	# and Zoom can be connected right now or not.
	#camera_dev = get_camera_dev()
	#capture_window = find_second_window()
	#obs.create_camera_scene(camera_dev)
	#obs.create_zoom_scene(capture_window)
	#obs.create_split_scene(camera_dev, capture_window)

	# The media list will already by in the cache. Get it.
	media = get_meeting_media_cached(docid)

	# Download in the background.
	run_thread(lambda: meeting_media_to_obs_scenes(media))

	return progress_callback_response("Loading media for %s..." % request.form.get("title"))

# Wrapper for get_meeting_media() which caches the responses in a DB table
def get_meeting_media_cached(docid):

	# Look for this meeting's media in the DB cache table
	# FIXME: Race condition can produce duplicate cache entries, so we use first().
	meeting = MeetingCache.query.filter_by(docid=docid).first()
	if meeting is not None:
		# Deserialize list from JSON back to objects
		for item in meeting.media:
			yield MeetingMedia(**item)
		return

	# Yield items as they are obtained by the underlying iterator.
	# Also save them in a list for the cache.
	media = []
	for item in get_meeting_media(docid):
		yield item
		media.append(item)

	# Serialize list from objects to JSON and store in DB cache table
	meeting = MeetingCache(docid=docid, media=list(map(lambda item: asdict(item), media)))
	db.session.add(meeting)
	db.session.commit()

# Download the meeting article (from the Watchtower or Workbook) and
# extract a list of the videos and images.
def get_meeting_media(docid):

	# Construct the sharing URL for the meeting article. This will redirect to the article itself.
	url = "https://www.jw.org/finder?wtlocale=U&docid={docid}&srcid=share".format(docid=docid)

	# Use the meeting loader to download the article and scan it for media
	# such as videos and illustrations. (Note that this is an iterator.)
	return meeting_loader.extract_media(url, callback=progress_callback)

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

