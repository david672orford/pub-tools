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
# close -- this is the last download in this group, close progress
def load_video_url(scene_name:str, url:str, thumbnail_url:str=None, prefix:str="▷", close:bool=True, skiplist:str=None):
	if scene_name is not None:
		progress_callback(_("Loading video \"{scene_name}\"...").format(scene_name=scene_name), cssclass="heading")

	video_metadata = meeting_loader.get_video_metadata(
		url,
		resolution = current_app.config["VIDEO_RESOLUTION"],
		)
	assert video_metadata is not None, "Failed to get metadata for %s" % url

	if scene_name is None:
		scene_name = video_metadata["title"]
		progress_callback(_("Video title is \"{scene_name}\".").format(scene_name=scene_name))

	progress_callback(_("Downloading \"{url}\"...").format(**video_metadata))
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)

	if thumbnail_url is None:
		thumbnail_url = video_metadata.get("thumbnail_url")
	if thumbnail_url is not None:
		progress_callback(_("Downloading \"{url}\"...").format(url=thumbnail_url))
		thumbnail = meeting_loader.download_media(thumbnail_url, callback=progress_callback)
	else:
		thumbnail = None

	# If SUB_LANGUAGE is set and the video is subtitled, enable them.
	subtitle_track = None
	sub_language = current_app.config["SUB_LANGUAGE"]
	if sub_language and video_metadata.get("subtitles_url") is not None:

		# Same language, enable the subtitles embedded in the MP4 file.
		if sub_language == meeting_loader.language:
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
			prefix + " " + scene_name,
			"video",
			video_file,
			thumbnail = thumbnail,
			subtitle_track = subtitle_track,
			skiplist = skiplist,
			)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))	
		progress_callback(_("✘ Loading of video failed."), last_message=close, cssclass="error")
	else:
		progress_callback(_("✔ Video has been loaded."), last_message=close, cssclass="success")

## Add a scene which plays a song from the songbook with onscreen lyrics
## The video will be downloaded, if it is not already in the cache.
## scene_name -- name of scene to create in OBS
## song -- song number
## close -- this is the last download in this group, close progress
#def load_song(song: int, close=True):
#	progress_callback(_("Loading song {song}...").format(song=song), cssclass="heading")
#	metadata = meeting_loader.get_song_metadata(song, resolution=current_app.config["VIDEO_RESOLUTION"])
#	progress_callback(_("Downloading \"{url}\"...").format(url=metadata["thumbnail_url"]))
#	thumbnail = meeting_loader.download_media(metadata["thumbnail_url"], callback=progress_callback)
#	progress_callback(_("Downloading \"{url}\"...").format(url=metadata["url"]))
#	media_file = meeting_loader.download_media(metadata["url"], callback=progress_callback)
#	try:
#		obs.add_media_scene(_("♫ Song") + " " + metadata["title"], "video", media_file, thumbnail=thumbnail, skiplist="*♫")
#	except ObsError as e:
#		flash(_("OBS: %s") % str(e))
#		progress_callback(_("✘ Loading of song failed."), last_message=close, cssclass="error")
#	else:
#		progress_callback(_("✔ Song {song} has been loaded.").format(song=song), last_message=close, cssclass="success")

# Add a scene which displays an image downloaded from the URL provided.
# Images from JW.ORG have unique names. Take care to assign non-colliding
# names to user-supplied images.
# scene_name -- name of scene to create in OBS
# url -- direct download link to the image file
# thumbnail_url -- link to a smaller version of the image (unused at present)
# close -- this is the last download in this group, close progress
def load_image_url(scene_name:str, url:str, thumbnail_url:str=None, skiplist:str=None, close:bool=True):
	progress_callback(_("Loading image \"{scene_name}\"...").format(scene_name=scene_name), cssclass="heading")
	try:
		image_file = meeting_loader.download_media(url, callback=progress_callback)
		obs.add_media_scene("□ " + scene_name, "image", image_file, skiplist=skiplist)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Loading of image failed."), last_message=close, cssclass="error")
	else:
		progress_callback(_("✔ Image has been loaded."), last_message=close, cssclass="success")

# Add a scene which displays a webpage from any site
# scene_name -- name of scene to create in OBS
# url -- address of web page
# thumbnail_url -- optional link to small image used in link to this webpage
# close -- this is the last download in this group, close progress
def load_webpage(scene_name:str, url:str, thumbnail_url:str=None, skiplist=None, close:bool=True):
	if scene_name is None:
		scene_name = meeting_loader.get_title(url)
	progress_callback(_("Loading webpage \"{scene_name}\"...").format(scene_name=scene_name), cssclass="heading")

	if thumbnail_url is not None:
		progress_callback(_("Downloading \"{url}\"...").format(url=thumbnail_url))
		thumbnail = meeting_loader.download_media(thumbnail_url, callback=progress_callback)
	else:
		thumbnail = None

	progress_callback(_("Loading webpage \"{scene_name}\"...").format(scene_name=scene_name))
	try:
		obs.add_media_scene("◯ " + scene_name, "web", url, thumbnail=thumbnail, skiplist=skiplist)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Loading of webpage failed."), last_message=close, cssclass="error")
	else:
		progress_callback(_("✔ Webpage has been loaded."), last_message=close, cssclass="success")

