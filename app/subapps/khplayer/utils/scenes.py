from flask import current_app
import os.path

from ....utils import progress_callback
from ....utils.babel import gettext as _
from ....utils.background import flash
from .controllers import meeting_loader, obs, ObsError

scene_name_prefixes = {
	"audio": "▷",
	"video": "▷",
	"image": "□ ",
	}

# Add a scene which plays a video from JW.ORG
# The video will be downloaded using the URL provided, if necessary.
# scene_name -- name of scene to create in OBS
# url -- a link to the video containing an "lank" or "docid" parameter
# thumbnail_url -- link to thumbnail image used to link to this video
# prefix -- media-type marker to put in front of scene name
# language -- optional language override, ISO code
# close -- this is the last download in this group, close progress
def load_video_url(scene_name, url, thumbnail_url=None, prefix="▷", language=None, close=True):
	progress_callback(_("Getting video download URL..."))
	video_metadata = meeting_loader.get_video_metadata(url, resolution=current_app.config["VIDEO_RESOLUTION"], language=language)
	assert video_metadata is not None, url

	progress_callback(_("Downloading video \"%s\"...") % video_metadata["title"])
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)

	sub_language = current_app.config["SUB_LANGUAGE"]
	subtitle_track = None
	if sub_language:
		# Same langauge, enable the subtitles embedded in the MP4 file, if there is a VTT file
		if sub_language == current_app.config["PUB_LANGUAGE"]:
			if "subtitles_url" in video_metadata:
				subtitle_track = 1

		# Different language. Download a VTT file, if one is available.
		else:
			sub_video_metadata = meeting_loader.get_video_metadata(url, language=sub_language)
			if sub_video_metadata["subtitles_url"] is not None:
				progress_callback(_("Downloading subtitles..."))
				subtitles_file = meeting_loader.download_media(sub_video_metadata["subtitles_url"], callback=progress_callback)
				os.rename(subtitles_file, os.path.splitext(video_file)[0] + ".vtt")
				subtitle_track = 2

	try:
		obs.add_media_scene(
			prefix + " " + (scene_name if scene_name is not None else video_metadata["title"]),
			"video",
			video_file,
			thumbnail_url = (thumbnail_url if thumbnail_url is not None else video_metadata.get("thumbnail_url")),
			subtitle_track = subtitle_track,
			)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))	
		progress_callback(_("Failed to add video"), last_message=close)
	else:
		progress_callback(_("Video loaded"), last_message=close)

# Add a scene which plays a song from the songbook with onscreen lyrics
# The video will be downloaded, if necessary.
# scene_name -- name of scene to create in OBS
# song -- song number
# close -- this is the last download in this group, close progress
def load_song(song: int, close=True):
	progress_callback(_("Getting song %d download URL...") % song)
	media_url = meeting_loader.get_song_video_url(song, resolution=current_app.config["VIDEO_RESOLUTION"])
	progress_callback(_("Downloading song %d...") % song)
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	try:
		obs.add_media_scene(_("♫ Song %s") % song, "video", media_file)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add song"), last_message=close)
	else:
		progress_callback(_("Song %d video loaded") % song, last_message=close)

# Add a scene which displays an image downloaded from the URL provided.
# Images from JW.ORG have unique names. Take care to assign non-colliding
# names to user-supplied images.
# scene_name -- name of scene to create in OBS
# url -- direct download link to the image file
# thumbnail_url -- link to a smaller version of the image
# close -- this is the last download in this group, close progress
def load_image_url(scene_name, url, thumbnail_url=None, close=True):
	try:
		progress_callback(_("Downloading image..."))
		image_file = meeting_loader.download_media(url, callback=progress_callback)
		obs.add_media_scene("□ " + scene_name, "image", image_file, thumbnail_url=thumbnail_url)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add image"), last_message=close)
	else:
		progress_callback(_("Image loaded"), last_message=close)

# Add a scene which displays a webpage from any site
# scene_name -- name of scene to create in OBS
# url -- address of web page
# thumbnail_url -- optional link to small image used in link to this webpage
# close -- this is the last download in this group, close progress
def load_webpage(scene_name, url, thumbnail_url=None, close=True):
	progress_callback(_("Loading webpage..."))
	if scene_name is None:
		scene_name = meeting_loader.get_title(url)
	try:
		obs.add_media_scene("◯ " + scene_name, "web", url, thumbnail_url=thumbnail_url)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Failed to add webpage"), last_message=close)
	else:
		progress_callback(_("Webpage loaded"), last_message=close)

