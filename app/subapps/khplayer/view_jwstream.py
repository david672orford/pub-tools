from flask import current_app, Blueprint, render_template, request, redirect, flash
from urllib.parse import urlencode
import os, re
from time import sleep
import subprocess
import logging

from ... import turbo
from ...utils import progress_callback, progress_response, run_thread, async_flash
from ...jworg.jwstream import StreamRequesterContainer
from ...utils.babel import gettext as _
from ...utils.config import get_config, put_config
from . import menu
from .views import blueprint
from .utils.controllers import obs

logger = logging.getLogger(__name__)

menu.append((_("JW Stream"), "/jwstream/"))

(
	# Languages
	_("Russian"),

	# Countries
	_("Ukraine"),
	_("Finland"),

	# Channels
	_("Congregation Meetings"),
	_("Public Talks"),

	# Meetings,
	_("Weekday Meeting"),
	_("Weekend Meeting"),
)

def jwstream_channels(config=None):
	if config is None:
		config = get_config("JW_STREAM")
	if not hasattr(jwstream_channels, "handle") or getattr(jwstream_channels, "urls", None) != config.get("urls"):
		try:
			jwstream_channels.handle = StreamRequesterContainer(config)
			jwstream_channels.url = config.get("urls")
		except Exception as e:
			logger.error(str(e))
			flash(str(e))
			jwstream_channels.handle = {}
	return jwstream_channels.handle

class ConfigForm(dict):
	defaults = {
		"preview_resolution": 234,	
		"download_resolution": 720,
		}
	resolutions = ((234, "416x234"), (360, "640x360"), (540, "960x540"), (720, "1280x720"))
	def __init__(self, config, data):
		self.update(self.defaults)
		if config is not None:
			self.update(config)
		if "urls" in data:
			self.update({
				"urls": "\n".join(data.get("urls").split()),
				"preview_resolution": int(data.get("preview_resolution")),
				"download_resolution": int(data.get("download_resolution")),
				})
	def validate(self):
		flashes = 0
		for url in self["urls"].split():
			m = re.match(r"^https://stream\.jw\.org/ts/[0-9a-zA-Z]{10}$", url)
			if m is None:
				flash(_("Not a JW Stream sharing URL: %s") % url)
				flashes += 1
		return flashes == 0

@blueprint.route("/jwstream/")
def page_jwstream():
	config = get_config("JW_STREAM")
	if request.args.get("action") == "configuration" or not "urls" in config:
		form = ConfigForm(config, request.args)
	else:
		form = None
	return render_template(
		"khplayer/jwstream.html",
		channels = jwstream_channels(config).values(),
		form = form,
		top = ".."
		)

@blueprint.route("/jwstream/save-config", methods=["POST"])
def page_jwstream_save_config():
	form = ConfigForm(None, request.form)
	if not form.validate():
		return redirect(".?action=configuration&" + urlencode(form))
	put_config("JW_STREAM", form)
	return redirect(".")

@blueprint.route("/jwstream/<token>/")
def page_jwstream_channel(token):
	channel = jwstream_channels()[token]
	events = channel.list_events()
	events = sorted(list(events), key=lambda item: (item.datetime, item.title))
	return render_template("khplayer/jwstream_events.html", channel=channel, events=events, top="../..")

# User has pressed Update button
@blueprint.route("/jwstream/<token>/update", methods=["POST"])
def page_jwstream_update(token):
	progress_callback(_("Updating event list..."))
	channel = jwstream_channels()[token]
	channel.reload()
	return progress_response(_("Channel event list updated."), last_message=True)

# Player
@blueprint.route("/jwstream/<token>/<id>/")
def page_jwstream_player(token, id):
	channel = jwstream_channels()[token]
	event = channel.get_event(id, preview=True)
	return render_template("khplayer/jwstream_player.html",
		id = id,
		channel = channel,
		event = event,
		clip_start = request.args.get("clip_start","0:00"),
		clip_end = request.args.get("clip_end","%d:%02d" % (int(event.duration / 60), event.duration % 60)),
		clip_title = request.args.get("clip_title", _(event.title)),
		top = "../../..",
		)

# When Make Clip button pressed
@blueprint.route("/jwstream/<token>/<id>/clip", methods=["POST"])
def page_jwstream_clip(token, id):
	clip_start = request.form.get("clip_start").strip()
	clip_end = request.form.get("clip_end").strip()
	clip_title = request.form.get("clip_title").strip()

	# URL which returns us to the form with the fill-in values preserved
	return_url = ".?" + urlencode(dict(clip_start=clip_start, clip_end=clip_end, clip_title=clip_title))

	try:
		try:
			t1 = parse_time(clip_start)
		except ValueError:
			raise ValueError(_("Invalid start time: %s") % clip_start)
		try:
			t2 = parse_time(clip_end)
		except ValueError:
			raise ValueError(_("Invalid end time: %s") % clip_end)
		clip_duration = t2 - t1
		if clip_duration <= 0:
			raise ValueError(_("Duration is zero or negative!"))
	except ValueError as e:
		flash(str(e))
		# Send the user back to try again while preserving what he entered.
		return redirect(return_url)

	# Ask stream.jw.org for the current URL of the full-resolution version.
	progress_callback(_("Requesting download URL..."))
	event = jwstream_channels()[token].get_event(id, preview=False)

	# If the user did not supply a clip title, make one from the video title and the start and end times.
	if not clip_title:
		clip_title = "%s %s-%s" % (event.title, clip_start, clip_end)

	# Spawn a background thread to download it and create the scene when the download is done.
	media_file = os.path.join(current_app.config["CACHEDIR"], "jwstream-%s-%s-%s.mp4" % (id, clip_start, clip_end))
	logger.debug("Downloading clip \"%s\" from %s to %s of \"%s\" in file %s" % (clip_title, clip_start, clip_end, event.title, media_file))
	progress_callback(_("Downloading clip..."))
	run_thread(lambda: download_clip(clip_title, event.download_url, media_file, clip_start, clip_end, clip_duration))

	# Go back to the player page in case the user wants to make another clip.
	return redirect(".")

def download_clip(clip_title, video_url, media_file, clip_start, clip_end, clip_duration):
	sleep(1)

	progress_callback(_("Downloading clip..."))

	# Use FFMpeg to download the part of the video file we need. This is possible
	# because FFMpeg can take a URL as input and the server supports range requests.
	cmd = [
		"ffmpeg", "-nostats", "-loglevel", "0", "-progress", "pipe:1",
			"-i", video_url,
			"-ss", clip_start,
			"-to", clip_end,
			"-c", "copy", media_file
		]
	logger.info("Download cmd: %s", cmd)
	ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
	for line in ffmpeg.stdout:
		logger.debug("Output: %s", line)
		m = re.match(r"out_time_us=(\d+)", line)
		if m:
			done = int(int(m.group(1)) / 1000000)
			progress_callback("{total_recv} of {total_expected}", total_recv=done, total_expected=clip_duration)
	ffmpeg_retcode = ffmpeg.wait()
	logger.info("FFmpeg exit code: %s", ffmpeg_retcode)

	# Sanity check: is the file there now?
	if not os.path.exists(media_file):
		progress_callback(_("Extraction of clip failed!"))

	else:
		try:
			obs.add_media_scene("▷" + " " + clip_title, "video", media_file)
		except ObsError as e:
			# FIXME: If the clip was downloaded previously, this will probably be erased immediately.
			async_flash("OBS: %s" % str(e))
		else:
			progress_callback(_("Clip created"), last_message=True)

# Parse a time string such as "4:45" into seconds
def parse_time(timestr):
	elements = timestr.split(":")
	if not 0 < len(elements) <= 3:
		raise ValueError
	seconds = 0
	for element in elements:
		if not re.match(r"^\d?\d$", element):
			raise ValueError
		value = int(element)
		if not 0 <= value < 60:
			raise ValueError
		seconds = (seconds * 60) + value
	return seconds

