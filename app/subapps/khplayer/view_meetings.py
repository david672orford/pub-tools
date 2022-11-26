from flask import render_template, request, redirect, flash
from datetime import date
from sqlalchemy import or_, and_
from datetime import date
from threading import Thread
import logging

from ... import app, turbo, progress_callback
from ...models import db, Weeks, MeetingCache
from ...cli_update import update_meetings
from .views import blueprint
from .utils import meeting_loader, obs, ObsError

logger = logging.getLogger(__name__)

# List upcoming meetings for which we can load media into OBS
@blueprint.route("/meetings/")
def page_meetings():
	weeks = Weeks.query
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))
	return render_template("khplayer/meetings.html", weeks=weeks.all(), top="..")

@blueprint.route("/meetings/update", methods=["POST"])
def page_meetings_update():
	update_meetings(callback=progress_callback)
	return redirect(".")

@blueprint.route("/meetings/<int:docid>/")
def page_meetings_view(docid):
	title = request.args.get("title")
	media = get_meeting_media_cached(docid)
	return render_template("khplayer/meeting_media.html", meeting_title=title, media=media, top="../..")

@blueprint.route("/meetings/<int:docid>/load", methods=['POST'])
def page_meetings_submit(docid):
	media = get_meeting_media_cached(docid)
	add_scenes(obs, media)
	return redirect(".")

def get_meeting_media_cached(docid):
	meeting = MeetingCache.query.filter_by(docid=docid).one_or_none()
	if meeting is not None:
		media = meeting.media
	else:
		media = get_meeting_media(docid)
		meeting = MeetingCache(docid=docid, media=media)
		db.session.add(meeting)
		db.session.commit()
	return media

def get_meeting_media(docid):
	progress_callback("Loading meeting...")
	url = "https://www.jw.org/finder?wtlocale=U&docid={docid}&srcid=share".format(docid=docid)
	scenes = meeting_loader.extract_media(url, callback=progress_callback)
	return scenes

def add_scenes(obs, scenes):
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
			#obs.add_scene(scene_name, media_type, media_url)
			pass
		else:						# video or image file
			media_file = meeting_loader.download_media(media_url, callback=progress_callback)
			obs.add_scene(scene_name, media_type, media_file)

