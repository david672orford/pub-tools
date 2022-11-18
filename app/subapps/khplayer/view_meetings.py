from flask import render_template, request, redirect, flash
from datetime import date
from sqlalchemy import or_, and_
from datetime import date
from threading import Thread
import logging

from ... import app, turbo
from ...models import Weeks
from .views import blueprint, meeting_loader, obs_connect

logger = logging.getLogger(__name__)

# List upcoming meetings for which we can load media into OBS
@blueprint.route("/meetings/")
def page_meetings():
	weeks = Weeks.query
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))
	return render_template("khplayer/meetings.html", weeks=weeks, top="..")

@blueprint.route("/meetings/submit", methods=['POST'])
def page_meetings_submit():
	url = None

	# Get the URL of the article (from the Watchtower or the Meeting Workbook)
	# which will be studied at this meeting.
	if request.form.get("action") == "add":
		url = request.form.get('url')
	elif 'docid' in request.form:
		docid = int(request.form.get('docid'))
		url = "https://www.jw.org/finder?wtlocale=U&docid=%s&srcid=share" % docid

	# If we have the article's URL, scan it and download the songs, videos,
	# and illustrations and add them to OBS as scenes.
	if url is not None:
		logger.info('Load meeting: %s', url)
		scenes = meeting_loader.extract_media(url)
		obs = obs_connect()
		if obs is not None:
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
					media_file = meeting_loader.download_media(media_url)
					obs.add_scene(scene_name, media_type, media_file)

	return redirect(".")

