from flask import current_app, Blueprint, render_template, request, redirect, flash

from .views import blueprint
from .utils import obs, ObsError
from .view_patchbay import patchbay
from .cameras import get_camera_dev
from .zoom import find_second_window
from .virtual_cable import connect_all
from ...utils import progress_callback

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

	except ObsError as e:
		flash("OBS: %s" % str(e))

	return redirect(".")

