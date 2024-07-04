from flask import current_app, render_template, request, redirect, stream_with_context
from datetime import date
from time import sleep
from sqlalchemy import or_, and_
from datetime import date
from threading import Thread
from dataclasses import asdict
from markupsafe import escape
import traceback
import logging

from ...utils.background import turbo, progress_callback, progress_response, run_thread, flash
from ...models import db, Weeks, MeetingCache
from ...cli_update import update_meetings
from ...utils.babel import gettext as _
from . import menu
from .views import blueprint
from .utils.controllers import meeting_loader, obs
from .utils.scenes import load_meeting_media_item
from ...jworg.meetings import MeetingMedia

logger = logging.getLogger(__name__)

menu.append((_("Meetings"), "/meetings/"))

# Construct a sharing URL for a meeting article. Sharing URL's redirect
# to the actual webpage of the article.
def meeting_url(docid):
	return "https://www.jw.org/finder?wtlocale={wtlocale}&docid={docid}&srcid=share".format(
		docid = docid,
		wtlocale = meeting_loader.meps_language,
		)

# List upcoming meetings
@blueprint.route("/meetings/")
def page_meetings():
	weeks = Weeks.query.filter_by(lang = meeting_loader.language)
	if not request.args.get("all", False):
		now_year, now_week, now_weekday = date.today().isocalendar()
		weeks = weeks.filter(or_(Weeks.year > now_year, and_(Weeks.year == now_year, Weeks.week >= now_week)))
	return render_template("khplayer/meetings.html", weeks=weeks.all(), top="..")

# Target for "Load More Weeks" button at bottom of upcoming meetings list
@blueprint.route("/meetings/update", methods=["POST"])
def page_meetings_update():
	progress_callback(_("Fetching meeting schedules..."), cssclass="heading")
	update_meetings(callback=progress_callback)
	return redirect(".")

# Show a particular upcoming meeting
@blueprint.route("/meetings/<int:docid>/")
def page_meetings_view(docid):
	title = request.args.get("title")
	return render_template(
		"khplayer/meetings_meeting.html",
		meeting_title = title,
		meeting_url = meeting_url(docid),
		top = "../.."
		)

# Asyncronous source which:
# 1) Downloads a meeting article
# 2) Extract the media list
# 3) Delivers items to a meeting's page using a Turbo Stream
# 4) Calls loaded_hook() in browser
@blueprint.route("/meetings/<int:docid>/stream")
def page_meetings_view_stream(docid):
	def streamer():
		progress_callback(_("Loading meeting media list..."), cssclass="heading")
		try:
			index = 0
			previous_section = None

			# Loop through the videos and illustrations which will be used in the meeting.
			for item in get_meeting_media(docid):

				# We use a small Jinja2 template to render the media item to HTML.
				data = render_template("khplayer/meetings_media_item.html",
					index = index,
					item = item,
					new_section = (item.section_title != previous_section),
					)

				# Send the media item to the page over the Turbo Stream.
				yield "data: " + data.replace("\n", " ") + "\n\n"

				# Slight pause so that loading is consistently visible even when meeting is loaded from cache
				sleep(.1)

				previous_section = item.section_title
				index += 1
		except Exception as e:
			logger.error(traceback.format_exc())
			flash(_("Error: %s" % e))
			progress_callback(_("✘ Unable to load meeting media list."), last_message=True, cssclass="error")
		else:
			progress_callback(_("✔ Meeting media list has finished loading."), last_message=True, cssclass="success")
			# Enable the Download Media and Create Scenes in OBS button.
			yield "data: " + turbo.append("<script>loaded_hook()</script>", target="button-box") + "\n\n"
	return current_app.response_class(stream_with_context(streamer()), content_type="text/event-stream")

# User has pressed the "Download Media and Create Scenes in OBS"
# button on a meeting's media page.
@blueprint.route("/meetings/<int:docid>/download", methods=["POST"])
def page_meetings_download(docid):

	# Remove all scenes except those with names beginning with an asterisk.
	# Such scenes are for stage cameras, Zoom, etc.
	if request.form.get("delete-existing","false") == "true":
		to_remove = []
		for scene in obs.get_scene_list()["scenes"]:
			if not scene["sceneName"].startswith("*"):
				to_remove.append(scene["sceneUuid"])
		obs.remove_scenes(to_remove)

	# The media list will already by in the cache. Loop over it collecting
	# only those items which have a checkbox next to them in the table.
	selected = set(map(int, request.form.getlist("selected")))
	media = []
	index = 0
	for item in get_meeting_media(docid):
		if index in selected:
			media.append(item)
		index += 1

	# Download in the background.
	run_thread(lambda: load_meeting_media(request.form.get("title"), media))

	return progress_response(None)

# Download the meeting article (from the Watchtower or Workbook) and
# extract a list of the videos and images. Implements caching.
def get_meeting_media(docid):

	# Look for this meeting's media in the DB cache table
	# FIXME: Race condition can produce duplicate cache entries, so we use first().
	meeting = MeetingCache.query.filter_by(lang=meeting_loader.language, docid=docid).first()
	if meeting is not None:
		progress_callback("Meeting is already in cache.")
		# Deserialize list from JSON back to objects
		for item in meeting.media:
			yield MeetingMedia(**item)
		return

	# Use the meeting loader to download the article and scan it for media
	# such as videos and illustrations. This is an iterator, so we can 
	# yield items as they are obtained. Also save them in a list for the cache.
	media = []
	for item in meeting_loader.extract_media(meeting_url(docid), callback=progress_callback):
		yield item
		media.append(item)

	# Serialize the meeting's media list to JSON and store in DB cache table
	meeting = MeetingCache(lang=meeting_loader.language, docid=docid, media=list(map(lambda item: asdict(item), media)))
	db.session.add(meeting)
	db.session.commit()

# This function is run in a background thread to download
# the media and add a scene in OBS for each item.
def load_meeting_media(title, items):
	progress_callback(_("Loading media for \"{title}\"...").format(title=title), cssclass="heading")
	for item in items:
		load_meeting_media_item(item)
	progress_callback(_("✔ All requested media have been loaded."), last_message=True, cssclass="success")

