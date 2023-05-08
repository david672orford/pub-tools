from flask import current_app, Blueprint, render_template, request, redirect, flash
import os, re
import subprocess
from urllib.parse import urlencode
import logging

from ... import turbo
from ...utils import progress_callback, progress_callback_response, run_thread
from ...jworg.jwstream import StreamRequester
from .views import blueprint
from .utils import obs

logger = logging.getLogger(__name__)

def jwstream_requester():
	if not hasattr(jwstream_requester, "handle"):
		if not "JW_STREAM" in current_app.config:
			flash("JW_STREAM not found in config.py")
			return None
		cachefile = os.path.join(current_app.instance_path, "jwstream-cache.json")
		try:
			jwstream_requester.handle = StreamRequester(current_app.config['JW_STREAM'], cachefile=cachefile) 
		except AssertionError as e:
			flash(str(e))
			jwstream_requester.handle = None
	return jwstream_requester.handle

@blueprint.route("/stream/")
def page_stream():
	requester = jwstream_requester()
	events = requester.get_events() if requester else []
	events = sorted(list(events), key=lambda item: (item.week_of[0], item.title))
	return render_template("khplayer/stream.html", events=events, top="..")

# User has pressed Update button
@blueprint.route("/stream/update", methods=["POST"])
def page_stream_update():
	progress_callback("Updating program list...")
	requester = jwstream_requester()
	if requester is not None:
		requester.reload()
		return progress_callback_response("Program list updated.")
	else:
		# Return to page so flash() message will be displayed
		return redirect(".")

@blueprint.route("/stream/<id>/")
def page_stream_player(id):
	event = jwstream_requester().get_event(id, preview=True)
	print("chapters:", event.chapters)
	return render_template("khplayer/stream_player.html",
		id=id,
		event=event,
		clip_start = request.args.get("clip_start",""),
		clip_end = request.args.get("clip_end",""),
		clip_title = request.args.get("clip_title",""),
		top="../..",
		)

@blueprint.route("/stream/<id>/clip", methods=["POST"])
def page_stream_clip(id):
	clip_start = request.form.get("clip_start").strip()
	clip_end = request.form.get("clip_end").strip()
	clip_title = request.form.get("clip_title").strip()

	# URL which returns us to the form with the fill-in values preserved
	return_url = ".?" + urlencode(dict(clip_start=clip_start, clip_end=clip_end, clip_title=clip_title))

	try:
		try:
			t1 = parse_time(clip_start)
		except ValueError:
			raise ValueError("Invalid start time: %s" % clip_start)
		try:
			t2 = parse_time(clip_end)
		except ValueError:
			raise ValueError("Invalid end time: %s" % clip_end)
		clip_duration = t2 - t1
		if clip_duration <= 0:
			raise ValueError("Duration is zero or negative!")
	except ValueError as e:
		flash(str(e))
		# Send the user back to try again while preserving what he entered.
		return redirect(return_url)

	# Ask stream.jw.org for the current URL of the full-resolution version.
	progress_callback("Requesting download URL...")
	event = jwstream_requester().get_event(id, preview=False)

	# If the user did not supply a clip title, make one from the video title and the start and end times.
	if not clip_title:
		clip_title = "%s %s-%s" % (event.title, clip_start, clip_end)

	# This is the file into which we will save the downloaded clip.
	media_file = os.path.join(current_app.config["CACHEDIR"], "jwstream-%s-%s-%s.mp4" % (id, clip_start, clip_end))

	logger.debug("Required clip \"%s\" from %s to %s of \"%s\" in file %s" % (clip_title, clip_start, clip_end, event.title, media_file))

	# If the this clip was made earlier, make the scene right away, otherwise
	# spawn a background thread to download it and create the scene when the
	# download is done.
	if os.path.exists(media_file):
		create_clip_scene(clip_title, media_file)
	else:
		run_thread(lambda: download_clip(clip_title, event.download_url, media_file, clip_start, clip_end, clip_duration))

	# Go back to the player page in case the user wants to make another clip.
	#return redirect(return_url)
	return redirect(".")

def download_clip(clip_title, video_url, media_file, clip_start, clip_end, clip_duration):
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
		progress_callback("Extraction of clip failed!")

	else:
		create_clip_scene(clip_title, media_file)

# Connect to OBS and tell it to make a new scene with this file as the input.
def create_clip_scene(clip_title, media_file):
	try:
		obs.add_media_scene("▷" + clip_title, "video", media_file)
	except ObsError as e:
		turbo_flash("OBS: %s" % str(e))
	else:
		progress_callback("Clip created")

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

