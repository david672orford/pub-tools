from io import BytesIO
import sys
import logging

from flask import request, Response, render_template, send_file

from .blueprint import blueprint
from .utils.zoom_tracker import ZoomTracker

logger = logging.getLogger(__name__)

def get_tracker() -> ZoomTracker|None:
	if not "khplayer-zoom-tracker" in sys.modules:
		return None
	tracker:ZoomTracker = sys.modules["khplayer-zoom-tracker"].zoom_tracker.tracker
	assert type(tracker) is ZoomTracker
	return tracker

@blueprint.route("/scenes/zoom/")
def page_scenes_zoom():
	return render_template("khplayer/scenes_zoom.html",
		tracker = get_tracker(),
		top="../..",
		)

@blueprint.route("/scenes/zoom/gallery.svg")
def page_scenes_zoom_gallery_svg():
	svg = render_template("khplayer/scenes_zoom.svg",
		tracker = get_tracker(),
		)
	return Response(svg, mimetype="image/svg+xml")

@blueprint.route("/scenes/zoom/gallery.png")
def page_scenes_zoom_gallery_png():
	image:BytesIO = get_tracker().get_gallery_image()
	return send_file(image, mimetype="image/jpeg")

@blueprint.route("/scenes/zoom/select", methods=["POST"])
def page_scenes_zoom_select():
	"""User click on participant image"""
	pos = int(request.args.get("pos"))
	get_tracker().set_speaker_index(pos)
	return {"result":"OK"}
