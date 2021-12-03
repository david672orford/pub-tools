from flask import render_template
from . import app

@app.route("/")
def index():
	return render_template("index.html", subapps=app.config['ENABLED_SUBAPPS'])

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@app.errorhandler(500)
def handle_500(error):
	return render_template("500.html"), 500

