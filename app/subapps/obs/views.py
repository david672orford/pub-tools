# Views for loading media from JW.ORG into OBS

from flask import Blueprint, render_template, request, Response, redirect
import os
import logging
from collections import defaultdict
from sqlalchemy import or_, and_
from datetime import date

from ...models import Weeks, Issues, Articles, Books, VideoCategories, Videos
from ... import app
from ...jworg.meetings import MeetingLoader

try:
	from .obs_api import ObsControl
except ModuleNotFoundError:
	from .obs_ws import ObsControl

logger = logging.getLogger(__name__)

blueprint = Blueprint('obs', __name__, template_folder="templates", static_folder="static")
blueprint.display_name = 'OBS'

meeting_loader = MeetingLoader(cachedir=app.cachedir)
obs_control = ObsControl()

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@blueprint.errorhandler(500)
def handle_500(error):
	return render_template("obs/500.html"), 500

# The Werkzeig developement server sometimes does not respond to a shutdown
# request until it gets the next HTTP request. So we use this instead.
# It is called from the OBS plugin to shut down the server thread.
@blueprint.route("/shutdown")
def shutdown():
	raise KeyboardInterrupt

@blueprint.route("/")
def page_index():
	return redirect("meetings/")

@blueprint.route("/meetings/", methods=['GET','POST'])
def page_meetings():

	url = None
	error = None

	# Get the URL of the article (from the Watchtower or the Meeting Workbook)
	# which will be studied at this meeting.
	if 'url' in request.args:
		url = request.args.get('url')
	elif 'docid' in request.args:
		docid = int(request.args.get('docid'))
		article = Articles.query.filter_by(docid=docid).one_or_none()
		if article is not None:
			url = article.href
		else:
			error = "Article for the requested week is not in the database."

	# If we have the article's URL, scan it and download the songs, videos,
	# and illustrations and add them to OBS as scenes.
	if url is not None:
		logger.info('Load meeting: %s', url)
		scenes = meeting_loader.extract_media(url)
		for scene_name, media_type, media_url in scenes:
			if media_type == "web":		# HTML page
				obs_control.add_scene(scene_name, media_type, media_url)
			else:						# video or image file
				media_file = meeting_loader.download_media(media_url)
				obs_control.add_scene(scene_name, media_type, media_file)

	weeks = Weeks.query
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))

	return render_template("obs/meetings.html", weeks=weeks, error=error, top="..")

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
	return render_template("obs/songs.html", videos=category.videos, top="..", error=error)

@blueprint.route("/videos/")
def page_videos():
	categories = defaultdict(list)
	for category in VideoCategories.query.order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[category.category_name].append((category.subcategory_name, category.category_key, category.subcategory_key))					
	return render_template("obs/video_categories.html", categories=categories.items(), top="..")

@blueprint.route("/videos/<category_key>/<subcategory_key>/")
def video_list(category_key, subcategory_key):
	error = None
	try:
		lank = request.args.get("lank")
		if lank:
			add_video(lank)
	except Exception as e:
		logger.exception("Failed to load video")
		error = str(e)
	category = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("obs/video_list.html", category=category, top="../../..", error=error)

# Download a video (if it is not already cached) and add it to OBS as a scene
def add_video(lank):
	video = Videos.query.filter_by(lank=lank).one()
	logger.info('Load video: "%s" "%s"', video.name, video.href)
	media_url = meeting_loader.get_video_url(video.href)
	media_file = meeting_loader.download_media(media_url)
	obs_control.add_scene(video.name, "video", media_file)

