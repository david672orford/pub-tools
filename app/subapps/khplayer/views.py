import sys
import traceback
import logging

from flask import current_app, render_template, redirect, make_response

from .blueprint import blueprint

logger = logging.getLogger(__name__)

@blueprint.route("/isup")
def page_isup():
	response = make_response("OK")
	response.headers["Access-Control-Allow-Origin"] = "*"
	return response

@blueprint.route("/")
def page_index():
	"""Redirect to default tab"""
	return redirect("scenes/")

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@blueprint.errorhandler(500)
def handle_500(error:Exception|int):
	return render_template(
		"khplayer/500.html",
		top="/khplayer",
		error = error,
		exception=traceback.format_exc(),
		), 500

from . import view_scenes
from . import view_scenes_composer
from . import view_scenes_zoom
from . import view_meetings
from . import view_jwstream
from . import view_songbook
from . import view_slides
from . import view_videos
if sys.platform == "linux" and current_app.config["PATCHBAY"]:
	from . import view_patchbay
	from . import view_patchbay_config
