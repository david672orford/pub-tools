from flask import current_app, Blueprint, render_template, request, redirect, flash
from time import sleep
import logging

from .views import blueprint, menu
from .utils import obs, ObsError
from .cameras import get_camera_dev
from .zoom import find_second_window
from .virtual_cable import patchbay, connect_all
from ...utils import progress_callback

logger = logging.getLogger(__name__)

menu.append(("Actions", "/actions/"))

@blueprint.route("/actions/")
def page_actions():
	return render_template(
		"khplayer/actions.html",
		top = ".."
		)

@blueprint.route("/actions/submit", methods=["POST"])
def page_actions_submit():
	try:
		match request.form.get("action"):

			case "reconnect-camera":
				camera_dev = get_camera_dev()
				if camera_dev is not None:
					obs.reconnect_camera(camera_dev)

			case "reconnect-zoom-capture":
				capture_window = find_second_window()
				if capture_window is not None:
					obs.reconnect_zoom_input(capture_window)

			case "reconnect-audio":
				patchbay.load()
				for failure in connect_all(patchbay, current_app.config["PERIPHERALS"]):
					flash(failure)

			case "add-camera":
				camera_dev = get_camera_dev()
				if camera_dev is not None:
					obs.create_camera_scene(camera_dev)
					sleep(1)
	
			case "add-zoom":
				capture_window = find_second_window()
				if capture_window is not None:
					obs.create_zoom_scene(capture_window)
					sleep(1)
	
			case "add-split":
				camera_dev = get_camera_dev()
				if camera_dev is not None:
					capture_window = find_second_window()
					if capture_window is not None:
						obs.create_split_scene(camera_dev, capture_window)
						sleep(1)

	except ObsError as e:
		flash("OBS: %s" % str(e))

	return redirect(".")

