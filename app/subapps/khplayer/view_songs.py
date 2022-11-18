from flask import render_template, request, redirect, flash
import logging

from ... import app, turbo
from ...models import VideoCategories
from .views import blueprint, meeting_loader, obs_connect, run_thread, download_progress_callback
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
		logger.info('Load song: "%s"', song)
		run_thread(lambda: load_song(song))

	# By clicking on link to video
	lank = request.form.get("lank")
	if lank:
		run_thread(lambda: load_video(lank))

	return redirect(".")

def load_song(song):
	download_progress_callback(message="Getting video URL...")
	media_url = meeting_loader.get_song_video_url(song)
	media_file = meeting_loader.download_media(media_url, callback=download_progress_callback)
	obs = obs_connect()
	if obs is not None:
		obs.add_scene("ПЕСНЯ %s" % song, "video", media_file)

