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

