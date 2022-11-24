from flask import request, session, render_template, redirect, flash
from time import sleep
import logging

from ... import app, turbo
from ...models import VideoCategories
from .views import blueprint
from .utils import meeting_loader, obs_connect, run_thread, make_progress_callback
from .view_videos import load_video

logger = logging.getLogger(__name__)

# List all the songs in the songbook. Clicking on a song loads it into OBS.
@blueprint.route("/songs/")
def page_songs():
	print("Session:", session)
	category = VideoCategories.query.filter_by(category_key="VODMusicVideos").filter_by(subcategory_key="VODSJJMeetings").one_or_none()
	return render_template("khplayer/songs.html", videos=category.videos if category else None, top="..")

@blueprint.route("/songs/submit", methods=["POST"])
def page_songs_submit():

	# By song number entered in form
	song = request.form.get('song')
	if song:
		logger.info('Load song: "%s"', song)
		progress_callback = make_progress_callback()
		run_thread(lambda: load_song(song, progress_callback))

	# By clicking on link to video
	lank = request.form.get("lank")
	if lank:
		progress_callback = make_progress_callback()
		run_thread(lambda: load_video(lank, progress_callback))

	return redirect(".")

def load_song(song, progress_callback):
	progress_callback("Getting song video URL...")
	media_url = meeting_loader.get_song_video_url(song)
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	obs = obs_connect(callback=progress_callback)
	if obs is not None:
		obs.add_scene("ПЕСНЯ %s" % song, "video", media_file)
		progress_callback("Song video loaded.")

