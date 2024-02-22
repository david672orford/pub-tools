from flask import request, session, render_template, redirect
import logging

from . import menu
from .views import blueprint
from ...utils.babel import gettext as _
from .utils.controllers import obs, ObsError

logger = logging.getLogger(__name__)

menu.append((_("Camera"), "/cameras/"))

@blueprint.route("/cameras/")
def page_cameras():
	return render_template("khplayer/cameras.html")

