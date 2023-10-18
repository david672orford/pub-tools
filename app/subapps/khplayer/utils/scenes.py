from ....utils import progress_callback, async_flash
from ....babel import gettext as _
from . import meeting_loader, obs, ObsError

def load_video(url, prefix="▷", close=True):
	progress_callback(_("Getting video download URL..."))
	video_metadata = meeting_loader.get_video_metadata(url, resolution="480p")
	assert video_metadata is not None, url
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)
	try:
		obs.add_media_scene(prefix + " " + video_metadata["title"], "video", video_file)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))	
	else:
		progress_callback(_("Video loaded"), last_message=close)

def load_song(song, close=True):
	progress_callback(_("Getting song video download URL..."))
	media_url = meeting_loader.get_song_video_url(song, resolution="480p")
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	try:
		obs.add_media_scene(_("♫ Song %s") % song, "video", media_file)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
	else:
		progress_callback(_("Song video loaded"), last_message=close)

def load_webpage(scene_name, url, close=True):
	try:
		obs.add_media_scene("◯ " + scene_name, "web", url)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
	else:
		progress_callback(_("webpage loaded"), last_message=close)

def load_image(scene_name, url, close=True):
	try:
		image_file = meeting_loader.download_media(url, callback=progress_callback)
		obs.add_media_scene("□ " + scene_name, "image", image_file)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
	else:
		progress_callback(_("Image loaded"), last_message=close)

