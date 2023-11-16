from flask import current_app
import os.path

from ....utils.babel import gettext as _
from ....utils.background import flash, progress_callback
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
	progress_callback(_("Requesting download URL for \"{scene_name}\"...").format(scene_name=scene_name))
	video_metadata = meeting_loader.get_video_metadata(url, resolution=current_app.config["VIDEO_RESOLUTION"], language=language)
	assert video_metadata is not None, url

	progress_callback(_("Downloading \"{url}\"...").format(**video_metadata))
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)

	# If subtitles have been enabled by setting SUB_LANGUAGE, enable them,
	# if they are available.
	subtitle_track = None
	sub_language = current_app.config["SUB_LANGUAGE"]
	if sub_language and video_metadata.get("subtitles_url") is not None:

		# Same language, enable the subtitles embedded in the MP4 file.
		if sub_language == current_app.config["PUB_LANGUAGE"]:
			subtitle_track = 1

		# Different language. Download a VTT file, if one is available.
		else:
			progress_callback(_("Requesting subtitles download url for \"{scene_name}\"...").format(scene_name=scene_name))
			sub_video_metadata = meeting_loader.get_video_metadata(url, language=sub_language)
			if sub_video_metadata.get("subtitles_url") is not None:
				progress_callback(_("Downloading subtitles from \"{subtitles_url}\"...").format(**sub_video_metadata))
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
		progress_callback(_("Unable to load video into OBS."), last_message=close)
	else:
		progress_callback(_("Video loaded into OBS."), last_message=close)

# Add a scene which plays a song from the songbook with onscreen lyrics
# The video will be downloaded, if necessary.
# scene_name -- name of scene to create in OBS
# song -- song number
# close -- this is the last download in this group, close progress
def load_song(song: int, close=True):
	progress_callback(_("Requesting download URL for song {song}...").format(song= song))
	media_url = meeting_loader.get_song_video_url(song, resolution=current_app.config["VIDEO_RESOLUTION"])
	progress_callback(_("Downloading \"{url}\"...").format(url=media_url))
	media_file = meeting_loader.download_media(media_url, callback=progress_callback)
	try:
		obs.add_media_scene(_("♫ Song %s") % song, "video", media_file)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Unable to song into OBS."), last_message=close)
	else:
		progress_callback(_("Song %d loaded into OBS.") % song, last_message=close)

# Add a scene which displays an image downloaded from the URL provided.
# Images from JW.ORG have unique names. Take care to assign non-colliding
# names to user-supplied images.
# scene_name -- name of scene to create in OBS
# url -- direct download link to the image file
# thumbnail_url -- link to a smaller version of the image
# close -- this is the last download in this group, close progress
def load_image_url(scene_name, url, thumbnail_url=None, close=True):
	try:
		progress_callback(_("Downloading image \"{scene_name}\"...").format(scene_name=scene_name))
		image_file = meeting_loader.download_media(url, callback=progress_callback)
		obs.add_media_scene("□ " + scene_name, "image", image_file, thumbnail_url=thumbnail_url)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Unable to load image into OBS."), last_message=close)
	else:
		progress_callback(_("Image loaded into OBS."), last_message=close)

# Add a scene which displays a webpage from any site
# scene_name -- name of scene to create in OBS
# url -- address of web page
# thumbnail_url -- optional link to small image used in link to this webpage
# close -- this is the last download in this group, close progress
def load_webpage(scene_name, url, thumbnail_url=None, close=True):
	progress_callback(_("Loading webpage \"{url}\"...").filter(url=url))
	if scene_name is None:
		scene_name = meeting_loader.get_title(url)
	try:
		obs.add_media_scene("◯ " + scene_name, "web", url, thumbnail_url=thumbnail_url)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("Unable to load webpage into OBS."), last_message=close)
	else:
		progress_callback(_("Webpage loaded into OBS."), last_message=close)

