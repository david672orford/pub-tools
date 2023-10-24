from flask import current_app
import os.path

from ....utils import progress_callback, async_flash
from ....utils.babel import gettext as _
from . import meeting_loader, obs, ObsError

def load_video(url, prefix="▷", close=True):
	progress_callback(_("Getting video download URL..."))
	video_metadata = meeting_loader.get_video_metadata(url, resolution="480p")
	print(video_metadata)
	assert video_metadata is not None, url

	progress_callback(_("Downloading video \"%s\"...") % video_metadata["title"])
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)

	enable_subtitles = current_app.config["ENABLE_SUBTITLES"]
	if enable_subtitles and video_metadata["subtitles_url"] is not None:
		progress_callback(_("Downloading subtitles..."))
		subtitles_file = meeting_loader.download_media(video_metadata["subtitles_url"], callback=progress_callback)
		os.rename(subtitles_file, os.path.splitext(video_file)[0] + ".vtt")

	try:
		obs.add_media_scene(prefix + " " + video_metadata["title"], "video", video_file, enable_subtitles=enable_subtitles)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))	
		progress_callback(_("Failed to add video"), last_message=close)
	else:
		progress_callback(_("Video loaded"), last_message=close)

def load_song(song, close=True):
	progress_callback(_("Getting song %d download URL...") % song)
	media_url = meeting_loader.get_song_video_url(song, resolution="480p")
	progress_callback(_("Downloading song %d...") % song)
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	try:
		obs.add_media_scene(_("♫ Song %s") % song, "video", media_file)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add song"), last_message=close)
	else:
		progress_callback(_("Song %d video loaded") % song, last_message=close)

def load_webpage(scene_name, url, close=True):
	progress_callback(_("Loading webpage..."))
	if scene_name is None:
		scene_name = meeting_loader.get_title(url)
	try:
		obs.add_media_scene("◯ " + scene_name, "web", url)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add webpage"), last_message=close)
	else:
		progress_callback(_("Webpage loaded"), last_message=close)

def load_image(scene_name, url, close=True):
	try:
		progress_callback(_("Downloading image..."))
		image_file = meeting_loader.download_media(url, callback=progress_callback)
		obs.add_media_scene("□ " + scene_name, "image", image_file)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add image"), last_message=close)
	else:
		progress_callback(_("Image loaded"), last_message=close)

