from flask import request, session, render_template, redirect
import re
import logging

from . import menu
from .views import blueprint
from ...utils.background import progress_callback, progress_response, run_thread, flash
from ...utils.babel import gettext as _
from .utils.controllers import meeting_loader, obs, ObsError
from .utils.scenes import load_video_url, load_song
from ...models import VideoCategories, Videos

logger = logging.getLogger(__name__)

menu.append((_("Songbook"), "/songs/"))

# List all the songs in the songbook. Clicking on a song loads it into OBS.
@blueprint.route("/songs/")
def page_songs():
	category = VideoCategories.query.filter_by(category_key="VODMusicVideos").filter_by(subcategory_key="VODSJJMeetings").one_or_none()
	return render_template("khplayer/songs.html", videos=category.videos if category else None, top="..")

@blueprint.route("/songs/submit", methods=["POST"])
def page_songs_submit():

	# By song number entered in form
	song = request.form.get('song')
	if song:
		song = song.strip()
		m = re.match(r"^(\d+)$", song)
		if not m:
			flash(_("Not a valid number: %s") % song)
			return redirect(".")
		song = int(m.group(1))
		if not (0 < song <= 151):
			flash(_("No such song: %s") % song)
			return redirect(".")
		run_thread(lambda: load_song(song))

	# By clicking on link to video
	lank = request.form.get("lank")
	if lank:
		video = Videos.query.filter_by(lank=lank).one()
		run_thread(lambda: load_video_url(None, video.href, prefix="♫ Песня"))

	return progress_response(None)

