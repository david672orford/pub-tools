import sys
import traceback
import logging

from flask import current_app, Blueprint, request, render_template, redirect
from flask_caching import Cache

logger = logging.getLogger(__name__)

blueprint = Blueprint("khplayer", __name__, template_folder="templates", static_folder="static")
blueprint.display_name = "KH Player"
blueprint.blurb = "Download videos and illustrations from JW.ORG and load them into OBS"

blueprint.cache = Cache()

# Redirect to default tab
@blueprint.route("/")
def page_index():
	return redirect("scenes/")

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@blueprint.errorhandler(500)
def handle_500(error):
	return render_template(
		"khplayer/500.html",
		top="/khplayer",
		exception=traceback.format_exc(),
		), 500

from . import view_scenes
from . import view_scenes_composer
from . import view_meetings
from . import view_jwstream
from . import view_songbook
from . import view_slides
from . import view_videos
if sys.platform == "linux" and current_app.config["PATCHBAY"]:
	from . import view_patchbay
	from . import view_patchbay_config
