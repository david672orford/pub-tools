from flask import Blueprint, render_template, request, redirect, flash
import os, re
import subprocess
from urllib.parse import urlencode
import logging

from ... import app, turbo, progress_callback
from ...jworg.jwstream import StreamRequester
from .views import blueprint
from .utils import obs

logger = logging.getLogger(__name__)

def jwstream_requester():
	if not hasattr(jwstream_requester, "handle"):
		if not "JW_STREAM" in app.config:
			flash("JW_STREAM not found in config.py")
			return None
		cachefile = os.path.join(app.instance_path, "jwstream-cache.json")
		try:
			jwstream_requester.handle = StreamRequester(app.config['JW_STREAM'], cachefile=cachefile) 
		except AssertionError as e:
			flash(str(e))
			jwstream_requester.handle = None
	return jwstream_requester.handle

@blueprint.route("/stream/")
def page_stream():
	requester = jwstream_requester()
	if requester and request.args.get("reload"):
		requester.reload()
	events = requester.get_events() if requester else []
	return render_template("khplayer/stream.html", events=events, top="..")

@blueprint.route("/stream/<int:id>/")
def page_stream_player(id):
	video_name, video_url, chapters = jwstream_requester().get_event(id, preview=True)
	return render_template("khplayer/stream_player.html",
		id=id,
		video_name=video_name,
		video_url=video_url,
		chapters=chapters,
		clip_start = request.args.get("clip_start",""),
		clip_end = request.args.get("clip_end",""),
		clip_title = request.args.get("clip_title",""),
		top="../..",
		)

@blueprint.route("/stream/<int:id>/clip", methods=["POST"])
def page_stream_clip(id):
	clip_start = request.form.get("clip_start").strip()
	clip_end = request.form.get("clip_end").strip()
	clip_title = request.form.get("clip_title").strip()
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
		# Send the user back to try again while preserving what he entered.
		flash(str(e))
		return redirect(return_url)

	# Ask stream.jw.org for the current URL of a low-resolution version
	# of the MP4 file suitable for preview use.
	video_name, video_url, chapters = jwstream_requester().get_event(id, preview=False)

	if not clip_title:
		clip_title = "%s %s-%s" % (video_name, clip_start, clip_end)

	# This is the file into which we will save the downloaded clip.
	media_file = os.path.join(app.cachedir, "jwstream-%d-%s-%s.mp4" % (id, clip_start, clip_end))

	print("Making clip \"%s\" from %s to %s of \"%s\" in file %s" % (clip_title, clip_start, clip_end, video_name, media_file))

	# If the file is not already in the cache, use FFMpeg to download the part
	# we need. The HTTP server supports seeking, so we do not have to download
	# the whole thing.
	if not os.path.exists(media_file):
		cmd = [
			"ffmpeg", "-nostats", "-loglevel", "0", "-progress", "pipe:1",
				"-i", video_url,
				"-ss", clip_start,
				"-to", clip_end,
				"-c", "copy", media_file
			]
		print("Download cmd:", cmd)
		ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
		for line in ffmpeg.stdout:
			print("Output:", line)
			m = re.match(r"out_time_us=(\d+)", line)
			if m:
				done = int(int(m.group(1)) / 1000000)
				progress_callback("%d of %d seconds" % (done, clip_duration))
		ffmpeg_retcode = ffmpeg.wait()
		print("FFmpeg done:", ffmpeg_retcode)

	# Sanity check: is the file there?
	if not os.path.exists(media_file):
		flash("Extraction of clip failed!")

	# Connect to OBS and tell it to make a new scene with this file as the input.
	try:
		obs.add_scene(clip_title, "video", media_file)
	except ObsError as e:
		flash("Communcation with OBS failed: %s" % str(e))

	# Go back to the player page in case the user wants to make another clip.
	return redirect(return_url)

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

