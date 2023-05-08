from flask import request, session, render_template, redirect, flash
from time import sleep
import logging

from ...utils import progress_callback, progress_callback_response, run_thread
from ...models import VideoCategories
from .views import blueprint
from .utils import meeting_loader, obs
from .view_videos import load_video

logger = logging.getLogger(__name__)

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
		message = 'Loading song %s' % song
		run_thread(lambda: load_song(song))

	# By clicking on link to video
	lank = request.form.get("lank")
	if lank:
		message = 'Loading song %s' % lank
		run_thread(lambda: load_video(lank))

	return progress_callback_response(message)

# Load a song video identified by song number
def load_song(song):
	progress_callback("Getting song video URL...")
	media_url = meeting_loader.get_song_video_url(song, resolution="480p")
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	try:
		obs.add_media_scene("♫ Песня %s" % song, "video", media_file)
	except ObsError as e:
		progress_callback("OBS: %s" % str(e))
	else:
		progress_callback("Song video loaded.")

