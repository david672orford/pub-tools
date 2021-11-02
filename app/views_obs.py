import os
from flask import render_template, request, Response, redirect
import logging
from collections import defaultdict
from . import app, obs_control, zoom_control, meeting_loader
from .models import Weeks, Issues, Articles, Videos, Books
from jwsite.epub import EpubLoader

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@app.errorhandler(500)
def handle_500(error):
	return render_template("obs/500.html"), 500

@app.route("/")
def page_index():
	return render_template("obs/index.html")

@app.route("/zoom")
def page_zoom():
	share = request.args.get("share")
	error = None
	try:
		if share == "on":
			zoom_control.start_screensharing()
		elif share == "off":
			zoom_control.stop_screensharing()
	except Exception as e:
		error = str(e)
	return render_template("obs/zoom.html", error=error, sharing=zoom_control.is_sharing())

@app.route("/obs", methods=['GET','POST'])
def page_obs():
	action = request.args.get("action")
	if action == "start_virtual_camera":
		obs_control.start_virtual_camera()
	return render_template("obs/obs.html")

@app.route("/songs", methods=['GET','POST'])
def page_songs():
	if request.method == 'POST':
		song = request.form['song']
		media_url = meeting_loader.get_song_video_url(song)
		media_file = meeting_loader.download_media(media_url)
		obs_control.add_scene("ПЕСНЯ %s" % song, media_file)
	return render_template("obs/songs.html")

@app.route("/meetings", methods=['GET','POST'])
def page_meetings():

	if 'url' in request.args:
		url = request.args.get('url')
	elif 'docid' in request.args:
		docid = int(request.args.get('docid'))
		article = Articles.query.filter_by(docid=docid).one()
		url = article.href
	else:
		url = None

	if url is not None:
		scenes = meeting_loader.extract_media(url)
		for scene_name, media_type, media_url in scenes:
			if media_type == "web":
				obs_control.add_scene(scene_name, media_type, media_url)
			else:
				media_file = meeting_loader.download_media(media_url)
				obs_control.add_scene(scene_name, media_type, media_file)

	return render_template("obs/meetings.html", weeks=Weeks.query)

@app.route("/videos")
def page_videos():
	lank = request.args.get("lank")
	if lank:
		video = Videos.query.filter_by(lank=lank).one()
		logger.info("Load video: \"%s\" \"%s\"", video.name, video.url)
		media_url = meeting_loader.get_video_url(video.url)
		media_file = meeting_loader.download_media(media_url)
		obs_control.add_scene(video.name, media_file)
	videos = defaultdict(list)
	for video in Videos.query.order_by(Videos.category, Videos.subcategory, Videos.name):
		videos[(video.category, video.subcategory)].append(video)
	return render_template("obs/videos.html", videos=videos)

@app.route("/epubs/")
def epub_index():
	return render_template("obs/epub_index.html", periodicals=Issues.query, books=Books.query)

@app.route("/epubs/<pub_code>/")
def epub_toc(pub_code):
	epub = open_epub(pub_code)
	id = request.args.get("id")
	if id is not None:
		for item in epub.opf.toc:
			if item.id == id:
				return redirect(item.href)
	return render_template("obs/epub_toc.html", epub=epub)

@app.route("/epubs/<pub_code>/<path:path>")
def epub_file(pub_code, path):
	epub = open_epub(pub_code)
	item = epub.opf.manifest_by_href.get(path)
	if item is None:
		abort(404)

	file_handle, content_length = epub.open(item.href)
	response = Response(file_handle, mimetype=item.mimetype)
	response.make_conditional(request, complete_length = content_length)
	return response

def open_epub(pub_code):
	if "-" in pub_code:
		pub_code, issue_code = pub_code.split("-",1)
		pub = Issues.query.filter_by(pub_code=pub_code).filter_by(issue_code=issue_code).one_or_none()
	else:
		pub = Books.query.filter_by(pub_code=pub_code).one_or_none()
	if pub is None:
		abort(404)
	return EpubLoader(os.path.join(app.cachedir, pub.epub_filename))

