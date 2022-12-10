from flask import Blueprint, render_template, request, redirect, flash
from time import sleep
import json

from .views import blueprint
from .pipewire import Patchbay

@blueprint.route("/patchbay/")
def page_patchbay():
	patchbay = Patchbay()
	return render_template("khplayer/patchbay.html", patchbay=patchbay, top="..")

