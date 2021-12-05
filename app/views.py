from flask import render_template
from . import app

@app.route("/")
def index():
	print(app.blueprints.items())
	subapps = [app.blueprints[bp] for bp in app.config['ENABLED_SUBAPPS']]
	return render_template("index.html", subapps=subapps)

