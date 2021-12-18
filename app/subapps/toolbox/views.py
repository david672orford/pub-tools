# Views for showing links to the Teaching Toolbox publications on JW.ORG

from flask import Blueprint, render_template
from collections import defaultdict
import logging
from ...models import Issues, Books, VideoCategories, Videos

logger = logging.getLogger(__name__)

blueprint = Blueprint('toolbox', __name__, template_folder="templates", static_folder="static")
blueprint.display_name = 'Toolbox'

@blueprint.route("/")
def toolbox():
	return render_template("toolbox/publications.html", path_prefix="./", categories=[
		("Приглашения", Books.query.filter(Books.name.like("Приглашение%")).order_by(Books.pub_code)),
		#("Видио", VideoCategories.query.filter_by(subcategory_key="VODMinistryTools").one_or_none().videos.order_by(Videos.lank)),
		("Видио", VideoCategories.query.filter_by(subcategory_key="VODMinistryTools").one_or_none().videos),
		("Книги", Books.query.filter(Books.pub_code.in_(("lffi", "ld", "ll", "bh","bhs","lv","lvs","jl"))).order_by(Books.pub_code)),
		("Буклеты", Books.query.filter(Books.pub_code.like("t-3%")).order_by(Books.pub_code)),
		("Сторожевая башня", Issues.query.filter_by(pub_code="wp").order_by(Issues.issue_code)),
		("Пробудуйтесь!", Issues.query.filter_by(pub_code="g").order_by(Issues.issue_code))
		])

@blueprint.route("/рабочая-тетрадь/")
def workbook():
	return render_template("toolbox/publications.html", path_prefix="../", categories=[
		("Рабочая тетрадь", Issues.query.filter_by(pub_code="mwb").order_by(Issues.issue_code))
		])

@blueprint.route("/видеоролики/")
def video_categories():
	categories = defaultdict(list)
	for category in VideoCategories.query.order_by(VideoCategories.category_name, VideoCategories.subcategory_name):
		categories[category.category_name].append((category.subcategory_name, category.category_key, category.subcategory_key))					
	return render_template("toolbox/video_categories.html", path_prefix="../", categories=categories.items())

@blueprint.route("/видеоролики/<category_key>/<subcategory_key>/")
def video_list(category_key, subcategory_key):
	category = VideoCategories.query.filter_by(category_key=category_key).filter_by(subcategory_key=subcategory_key).one_or_none()
	return render_template("toolbox/video_list.html", path_prefix="../../../", category=category)

