from flask import Blueprint, render_template, request, redirect, flash
import os
import subprocess
import logging

from ... import app, turbo
from ...jworg.jwstream import StreamRequester
from .views import blueprint, obs_connect

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

@blueprint.route("/stream/<int:id>")
def page_stream_player(id):
	video_name, video_url, chapters = jwstream_requester().get_event(id, preview=True)
	print(video_name, video_url)
	return render_template("khplayer/stream_player.html", id=id, video_name=video_name, video_url=video_url, chapters=chapters, top="..")

@blueprint.route("/stream/<int:id>/trim", methods=["POST"])
def page_stream_trim(id):
	video_name, video_url, chapters = jwstream_requester().get_event(id, preview=False)
	start = request.form.get("start")
	end = request.form.get("end")
	video_name = "%s %s-%s" % (video_name, start, end)
	media_file = os.path.join(app.cachedir, "jwstream-%d-%s-%s.mp4" % (id, start, end))
	if not os.path.exists(media_file):
		result = subprocess.run(["ffmpeg", "-i", video_url, "-ss", start, "-to", end, "-c", "copy", media_file])
	obs = obs_connect()
	if obs is not None:
		obs.add_scene(video_name, "video", media_file)
	return redirect("..")

