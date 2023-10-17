from flask import request, session, render_template, redirect
from time import sleep
import logging

from ...utils import progress_callback, progress_response, run_thread, async_flash
from ...models import VideoCategories
from ...babel import gettext as _
from .views import blueprint, menu
from .utils import meeting_loader, obs, ObsError, load_video

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
		message = _("Loading song %s") % song
		run_thread(lambda: load_song(song))

	# By clicking on link to video
	lank = request.form.get("lank")
	if lank:
		message = _("Loading song %s") % lank
		run_thread(lambda: load_video(lank, prefix="♫ ПЕСНЯ "))

	return progress_response(message)

# Load a song video identified by song number
def load_song(song):
	progress_callback(_("Getting song video URL..."))
	media_url = meeting_loader.get_song_video_url(song, resolution="480p")
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	try:
		obs.add_media_scene(_("♫ Song %s") % song, "video", media_file)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
	else:
		progress_callback(_("Song video loaded"), last_message=True)

