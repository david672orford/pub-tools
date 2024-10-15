import re
from time import sleep
import logging

from flask import current_app, request, session, render_template, redirect

from . import menu
from .views import blueprint
from ...utils.background import progress_callback, progress_response, run_thread, flash
from ...utils.babel import gettext as _
from .utils.controllers import meeting_loader, obs, ObsError
from .utils.scenes import load_video_url
from ...cli_jworg import update_video_subcategory
from ...models import VideoCategories, Videos

logger = logging.getLogger(__name__)

menu.append((_("Songbook"), "/songbook/"))

# List all the songs in the songbook. Clicking on a song loads it into OBS.
@blueprint.route("/songbook/")
def page_songbook():
	category = VideoCategories.query.filter_by(
		lang = meeting_loader.language,
		category_key = "VODMusicVideos",
		subcategory_key = "VODSJJMeetings",
		).one_or_none()
	return render_template("khplayer/songbook.html", videos=category.videos if category else None, top="..")

@blueprint.route("/songbook/update", methods=["POST"])
def page_songbook_update():
	progress_callback(_("Updating song list..."), cssclass="heading")
	update_video_subcategory(meeting_loader.language, "VODMusicVideos", "VODSJJMeetings", callback=progress_callback)
	progress_callback(_("✔ Song list updated."), cssclass="success", close=True)
	sleep(2)
	return redirect(".")

@blueprint.route("/songbook/submit", methods=["POST"])
def page_songbook_submit():
	video = None

	# If user entered a song number into the form,
	song = request.form.get("song")
	if song:
		m = re.match(r"^\s*(\d+)\s*$", song)
		if not m:
			flash(_("Not a number: {song}").format(song=song))
			return redirect(".")
		song = int(m.group(1))
		video = Videos.query.filter_by(lang=meeting_loader.language, lank=f"pub-sjjm_{song}_VIDEO").one_or_none()
		if video is None:
			flash(_("No such song: {song}").format(song=song))

	# If the user clicked on a link to a song,
	lank = request.form.get("lank")
	if lank:
		video = Videos.query.filter_by(lang=meeting_loader.language, lank=lank).one()

	if video:
		run_thread(lambda: load_video_url(
			video.title,
			video.href,
			prefix = "♫",
			# Load after cameras as opening song or after opening song
			skiplist = "*♫",
			))

	return progress_response(None)

