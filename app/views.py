from flask import render_template
from . import app
from .models import Publications

@app.route("/")
def index():
	return render_template("publications.html", categories=[("все", Publications.query)])

