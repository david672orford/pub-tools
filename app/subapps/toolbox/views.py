# Views for showing links to the Teaching Toolbox publications on JW.ORG

from flask import Blueprint, render_template
import logging
from ...models import Issues, Books, Videos

logger = logging.getLogger(__name__)

blueprint = Blueprint('toolbox', __name__, template_folder="templates", static_folder="static")

@blueprint.route("/")
def toolbox():
	return render_template("publications.html", categories=[
		#("Приглашения", Books.query.filter(Books.name.like("Приглашение%")).order_by(Books.pub_code)),
		("Видио", Videos.query.filter_by(category="VODMinistryTools").order_by(Videos.lank)),
		("Книги", Books.query.filter(Books.pub_code.in_(("lffi", "ld", "ll", "bh","bhs","lv","lvs","jl"))).order_by(Books.pub_code)),
		#("Буклеты", Books.query.filter(Books.pub_code.like("t-3%")).order_by(Books.pub_code)),
		("Сторожевая башня", Issues.query.filter_by(pub_code="wp").order_by(Issues.issue_code)),
		("Пробудуйтесь!", Issues.query.filter_by(pub_code="g").order_by(Issues.issue_code))
		])

@blueprint.route("/рабочая-тетрадь")
def workbook():
	return render_template("publications.html", categories=[
		("Рабочая тетрадь", Issues.query.filter_by(code="mwb").order_by(Issues.issue_code))
		])

@blueprint.route("/видеоролики")
def videos():
	return render_template("videos.html", videos=Videos.query.order_by(Videos.category, Videos.subcategory, Videos.name))

