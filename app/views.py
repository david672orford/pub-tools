from flask import current_app, Blueprint, render_template

blueprint = Blueprint("Pub-Tools", __name__)

def init_app(app):
	app.register_blueprint(blueprint)

@blueprint.route("/")
def index():
	subapps = [current_app.blueprints[bp] for bp in current_app.config['ENABLED_SUBAPPS']]
	return render_template("index.html", subapps=subapps)

