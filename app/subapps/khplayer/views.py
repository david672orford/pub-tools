# Views for loading media from JW.ORG into OBS

from flask import Blueprint, render_template, request, Response, redirect
import os
import logging
from collections import defaultdict
from sqlalchemy import or_, and_
from datetime import date
from urllib.parse import urlencode
import subprocess

from ...models import Weeks, Articles, VideoCategories, Videos
from ... import app, socketio
from ...jworg.meetings import MeetingLoader
from ...jworg.jwstream import StreamRequester

# Load a client API for controlling OBS. There are two versions of it.
# The first in obs_api.py works when we are running inside OBS. The
# second which is in obs_ws.py is what we use when we are running outside.
# It communicates with OBS through the OBS Websocket plugin.
try:
	from .obs_api import ObsControl
except ModuleNotFoundError:
	#from .obs_ws_4 import ObsControl
	from .obs_ws_5 import ObsControl, OBSError

logger = logging.getLogger(__name__)

blueprint = Blueprint('khplayer', __name__, template_folder="templates", static_folder="static")
blueprint.display_name = 'KH Player'

meeting_loader = MeetingLoader(cachedir=app.cachedir)
obs_control = ObsControl(config=app.config.get("OBS_WEBSOCKET"))

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@blueprint.errorhandler(500)
def handle_500(error):
	return render_template("khplayer/500.html", top=".."), 500

# Redirect to default tab
@blueprint.route("/")
def page_index():
	return redirect("meetings/")

#======================================================
# Meetings Tab
#======================================================

# List upcoming meetings for which we can load media into OBS
@blueprint.route("/meetings/")
def page_meetings():
	error = request.args.get("error")
	weeks = Weeks.query
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))
	return render_template("khplayer/meetings.html", weeks=weeks, error=error, top="..")

@blueprint.route("/meetings/submit", methods=['POST'])
def page_meetings_submit():
	url = None
	error = None

	# Get the URL of the article (from the Watchtower or the Meeting Workbook)
	# which will be studied at this meeting.
	if request.form.get("action") == "add":
		url = request.form.get('url')
	elif 'docid' in request.form:
		docid = int(request.form.get('docid'))

		# First attempt, requires us to index all Watchtower and MWB articles in the DB
		#article = Articles.query.filter_by(docid=docid).one_or_none()
		#if article is not None:
		#	url = article.href
		#else:
		#	error = "Article for the requested week is not in the database."

		# Second attempt, WOL pages are harder to interpret since the HTML attribute reveal less
		#week = Weeks.query.filter(or_(Weeks.watchtower_docid==docid, Weeks.mwb_docid==docid)).one()
		#if week.watchtower_docid == docid:
		#	url = week.watchtower_url
		#elif week.mwb_docid == docid:
		#	url = week.mwb_url

		# Third attempt, use sharing URL of version on main site
		url = "https://www.jw.org/finder?wtlocale=U&docid=%s&srcid=share" % docid

	# If we have the article's URL, scan it and download the songs, videos,
	# and illustrations and add them to OBS as scenes.
	if url is not None:
		logger.info('Load meeting: %s', url)
		scenes = meeting_loader.extract_media(url)
		for scene in scenes:
			print(scene)
			pub_code, scene_name, media_type, media_url = scene

			# Add a symbol to the front of the scene name to indicate its type.
			print(pub_code, scene_name, media_type, media_url)
			if pub_code is not None and pub_code.startswith("sjj"):
				scene_name = "♫ " + scene_name
			elif media_type == "video":
				scene_name = "▷ " + scene_name
			elif media_type == "image":
				scene_name = "□ " + scene_name	

			if media_type == "web":		# HTML page
				#obs_control.add_scene(scene_name, media_type, media_url)
				pass
			else:						# video or image file
				media_file = meeting_loader.download_media(media_url)
				obs_control.add_scene(scene_name, media_type, media_file)

	if error is not None:
		return redirect(".?%s" % urlencode({"error": error}))
	return redirect(".")

#======================================================
# Songs Tab
#======================================================

# List all the songs in the songbook. Clicking on a song loads it into OBS.
@blueprint.route("/songs/", methods=['GET','POST'])
def page_songs():
	error = None
	try:
		# By song number entered in form
		if request.method == 'POST' and 'song' in request.form:
			song = request.form['song']
			logger.info('Load song: "%s"', song)
			media_url = meeting_loader.get_song_video_url(song)
			media_file = meeting_loader.download_media(media_url)
			obs_control.add_scene("ПЕСНЯ %s" % song, "video", media_file)

		# By clicking on link to video
		lank = request.args.get("lank")
		if lank:
			add_video(lank)

	except Exception as e:
		logger.exception("Failed to load song video")
		error = str(e)

	category = VideoCategories.query.filter_by(category_key="VODMusicVideos").filter_by(subcategory_key="VODSJJMeetings").one_or_none()
	return render_template("khplayer/songs.html", videos=category.videos if category else None, top="..", error=error)

#======================================================
# Videos Tab
#======================================================

# List all the categories of videos on JW.org.
@blueprint.route("/videos/")
def page_video_categories():
	categories = defaultdict(list)
	for category in VideoCategories.query.order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[category.category_name].append((category.subcategory_name, category.category_key, category.subcategory_key))					
	return render_template("khplayer/video_categories.html", categories=categories.items(), top="..")

# List all the videos in a category. Clicking on a video loads it into OBS.
@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def page_video_list(category_key, subcategory_key):
	error = None
	try:
		lank = request.args.get("lank")
		if lank:
			add_video(lank)
	except Exception as e:
		logger.exception("Failed to load video")
		error = str(e)
	category = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("khplayer/video_list.html", category=category, top="../../..", error=error)

# Download a video (if it is not already cached) and add it to OBS as a scene
def add_video(lank):
	video = Videos.query.filter_by(lank=lank).one()
	logger.info('Load video: "%s" "%s"', video.name, video.href)
	media_url = meeting_loader.get_video_url(video.href)
	media_file = meeting_loader.download_media(media_url)
	obs_control.add_scene(video.name, "video", media_file)

#======================================================
# Stream
#======================================================

def make_jwstream_requester():
	cachefile = os.path.join(app.instance_path, "jwstream-cache.json")
	requester = StreamRequester(app.config['JW_STREAM']['url'], cachefile=cachefile) 
	requester.connect()
	return requester

@blueprint.route("/stream/")
def page_stream():
	requester = make_jwstream_requester()
	return render_template("khplayer/stream.html", events=requester.get_events(), top="..")

@blueprint.route("/stream/<int:id>")
def page_stream_player(id):
	requester = make_jwstream_requester()
	video_name, video_url, chapters = requester.get_event(id, 234)
	return render_template("khplayer/stream_player.html", id=id, video_name=video_name, video_url=video_url, chapters=chapters, top="..")

@blueprint.route("/stream/<int:id>/trim", methods=["POST"])
def page_stream_trim(id):
	requester = make_jwstream_requester()
	video_name, video_url, chapters = requester.get_event(id, 720)
	start = request.form.get("start")
	end = request.form.get("end")
	video_name = "%s %s-%s" % (video_name, start, end)
	media_file = os.path.join(app.cachedir, "jwstream-%d-%s-%s.mp4" % (id, start, end))
	if not os.path.exists(media_file):
		result = subprocess.run(["ffmpeg", "-i", video_url, "-ss", start, "-to", end, "-c", "copy", media_file])
	obs_control.add_scene(video_name, "video", media_file)
	return redirect("..")

#======================================================
# OBS Tab
#======================================================

@blueprint.route("/obs/")
def page_obs():
	obs_control.connect()
	scenes = reversed(obs_control.ws.get_scene_list().scenes)
	return render_template("khplayer/obs.html", scenes=scenes, top="..")

@blueprint.route("/obs/submit", methods=["POST"])
def page_obs_submit():
	action = request.form.get("action")
	print("action:", action)

	obs_control.connect()

	if action == "delete":
		for scene in request.form.getlist("del"):
			print(scene)
			try:
				obs_control.ws.remove_scene(scene)
			except OBSError:
				pass

	elif action == "delete-all":
		for scene in obs_control.ws.get_scene_list().scenes:
			print(scene)
			obs_control.ws.remove_scene(scene["sceneName"])

	elif action == "new":
		collection = request.form.get("collection").strip()
		if collection != "":
			obs_control.ws.create_scene_collection(collection)

	return redirect(".")

