from flask import current_app
import os.path
import logging
from urllib.parse import urlparse, parse_qsl, unquote

from ....jworg.meetings import MeetingMediaItem
from ....utils.babel import gettext as _
from ....utils.background import flash, progress_callback, progress_response
from .controllers import meeting_loader, obs, ObsError

logger = logging.getLogger(__name__)

scene_name_prefixes = {
	"audio": "▷",
	"video": "▷",
	"image": "□ ",
	"pdf": "□ ",
	}

# Add a scene which plays a video from JW.ORG
# The video will be downloaded using the URL provided, if necessary.
# scene_name -- name of scene to create in OBS
# url -- a link to the video containing an "lank" or "docid" parameter
#        (or a sharing URL pointing to publication and track)
# thumbnail_url -- link to thumbnail image (used for fallback)
#        (or a local file path starting with "/")
# prefix -- media-type marker to put in front of scene name
# close -- this is the last download in this group, close progress
def load_video_url(scene_name:str, url:str, thumbnail_url:str=None, prefix:str="▷", close:bool=True, skiplist:str=None):
	loading_video_message = _("Loading video \"{scene_name}\"...")

	if scene_name is not None:
		progress_callback(loading_video_message.format(scene_name=scene_name), cssclass="heading")

	video_metadata = meeting_loader.get_video_metadata(
		url,
		resolution = current_app.config["VIDEO_RESOLUTION"],
		)
	assert video_metadata is not None, "Can't get metadata for %s" % url
	logger.info("video_metadata: %s", video_metadata)

	if scene_name is None:
		scene_name = video_metadata["title"]
		progress_callback(loading_video_message.format(scene_name=scene_name), cssclass="heading")

	progress_callback(_("Downloading \"{url}\"...").format(url=unquote(video_metadata["url"])))
	video_file = meeting_loader.download_media(video_metadata["url"], callback=progress_callback)

	if thumbnail_url is None:
		thumbnail_url = video_metadata["thumbnail_url"]

	if thumbnail_url is None:				# Still no thumbnail
		thumbnail_file = None
	elif thumbnail_url.startswith("/"):		# Caller-supplied thumbnail
		thumbnail_file = thumbnail_url
	else:									# Downloadable thumbnail
		progress_callback(_("Downloading \"{url}\"...").format(url=unquote(thumbnail_url)))
		thumbnail_file = meeting_loader.download_media(thumbnail_url, callback=progress_callback)

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

	load_video_file(scene_name, video_file, thumbnail_file, subtitle_track, prefix, close, skiplist)

def load_video_file(scene_name:str, video_file:str, thumbnail_file:str=None, subtitle_track:str=None, prefix:str="▷", close:bool=True, skiplist:str=None):
	try:
		obs.add_media_scene(
			prefix + " " + scene_name,
			"video",
			video_file,
			thumbnail = thumbnail_file,
			subtitle_track = subtitle_track,
			skiplist = skiplist,
			)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Loading of video failed."), last_message=close, cssclass="error")
	else:
		progress_callback(_("✔ Video has been loaded."), last_message=close, cssclass="success")

# Add a scene which displays an image downloaded from the URL provided.
# Images from JW.ORG have unique names, so we don't worry about colisions.
# scene_name -- name of scene to create in OBS
# url -- direct download link to the image file
# thumbnail_url -- link to a smaller version of the image (unused at present)
# close -- this is the last download in this group, close progress
def load_image_url(scene_name:str, url:str, thumbnail_url:str=None, skiplist:str=None, close:bool=True):
	#assert thumbnail_url is None, "not supported yet"
	progress_callback(_("Loading image \"{scene_name}\"...").format(scene_name=scene_name), cssclass="heading")
	image_file = meeting_loader.download_media(url, callback=progress_callback)
	load_image_file(scene_name, image_file, None, skiplist, close)

def load_image_file(scene_name:str, image_file:str, thumbnail_file:str=None, skiplist:str=None, close:bool=True):
	assert thumbnail_file is None, "not supported yet"
	try:
		obs.add_media_scene(
			"□ " + scene_name,
			"image",
			image_file,
			skiplist = skiplist,
			)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Loading of image failed."), last_message=close, cssclass="error")
	else:
		progress_callback(_("✔ Image has been loaded."), last_message=close, cssclass="success")

def load_media_file(scene_name:str, media_file:str, mimetype:str, thumbnail_file:str=None, skiplist:str=None, close:bool=True):
	"""Generic loader for files supplied by user"""
	if mimetype == "application/pdf":
		mediatype = "pdf"
	else:
		mediatype = mimetype.split("/")[0]
	scene_name_prefix = scene_name_prefixes[mediatype]
	try:
		obs.add_media_scene(
			scene_name_prefix + " " + scene_name,
			mediatype,
			media_file,
			thumbnail = thumbnail_file,
			skiplist = skiplist,
			)
	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))
		progress_callback(_("✘ Loading of \"%s\" failed.") % scene_name, last_message=close, cssclass="error")
	else:
		progress_callback(_("✔ \"%s\" has been loaded.") % scene_name, last_message=close, cssclass="success")

# Add a scene which displays a webpage from any site
# scene_name -- name of scene to create in OBS
# url -- address of web page
# thumbnail_url -- optional link to small image used in link to this webpage
# close -- this is the last download in this group, close progress
def load_webpage(scene_name:str, url:str, thumbnail_url:str=None, skiplist=None, close:bool=True):
	if scene_name is None or thumbnail_url is None:
		metadata = meeting_loader.get_webpage_metadata(url)
	if scene_name is None:
		scene_name = metadata.title
	if thumbnail_url is None:
		thumbnail_url = metadata.thumbnail_url
	progress_callback(_("Loading webpage \"{scene_name}\"...").format(scene_name=scene_name), cssclass="heading")

	if thumbnail_url is not None:
		progress_callback(_("Downloading \"{url}\"...").format(url=unquote(thumbnail_url)))
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

# Add a scene which displays text
# scene_name -- name of scene to create in OBS
# text -- the text to display
def load_text(scene_name, text):
	scene_uuid = obs.create_scene(scene_name, make_unique=True)["sceneUuid"]
	source = obs.create_unique_input(
		scene_uuid = scene_uuid,
		input_name = "Text Source",
		input_kind = "text_ft2_source_v2",
		input_settings = {
			"font": {
				 "face": "Sans Serif",
				 "flags": 0,
				 "size": 72,
				 "style": ""
				},
			"custom_width": 1200,
			"drop_shadow": False,
			"outline": False,
			"text": text,
			"word_wrap": True
			}
		)
	obs.scale_scene_item(scene_uuid, source["sceneItemId"], scene_item_transform={
		"positionX": 40,
		"positionY": 40,
		"boundsWidth": 1200,
		"boundsHeight": 640,
		"alignment": 5,
		"boundsAlignment": 4,
		"boundsType": "OBS_BOUNDS_SCALE_TO_WIDTH",
		})

	return progress_response(_("✔ Text has been added."), last_message=True, cssclass="success")

def load_meeting_media_item(item:MeetingMediaItem):
	assert isinstance(item, MeetingMediaItem)
	logger.info("Loading media item: %s", repr(item))
	if item.media_type == "web":		# HTML page
		load_webpage(item.title, item.media_url, thumbnail_url=item.thumbnail_url, close=False)
	elif item.pub_code is not None and item.pub_code.startswith("sjj"):
		load_video_url(item.title, item.media_url, thumbnail_url=item.thumbnail_url, prefix="♫ ", close=False)
	elif item.media_type == "video":
		load_video_url(item.title, item.media_url, thumbnail_url=item.thumbnail_url, close=False)
	elif item.media_type == "image":
		load_image_url(item.title, item.media_url, thumbnail_url=item.thumbnail_url, close=False)
	else:
		raise AssertionError("Unhandled case")
