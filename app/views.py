from flask import current_app, Blueprint, request, Response, render_template

blueprint = Blueprint("Pub-Tools", __name__)

def init_app(app):
	app.register_blueprint(blueprint)

@blueprint.route("/")
def index():
	subapps = [current_app.blueprints[bp] for bp in current_app.config['ENABLED_SUBAPPS']]
	return render_template("index.html", subapps=subapps)

@blueprint.route("/debug")
def debug():
    return Response("\n".join(map(str, request.environ.items())), mimetype="text/plain")

