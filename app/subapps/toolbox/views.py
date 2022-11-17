# Views for showing links to the Teaching Toolbox publications on JW.ORG

from flask import Blueprint, render_template, redirect
import logging
from ...models import PeriodicalIssues, Books, VideoCategories, Videos

logger = logging.getLogger(__name__)

blueprint = Blueprint('toolbox', __name__, template_folder="templates", static_folder="static")
blueprint.display_name = 'Toolbox'
blueprint.blurb = "Get lists of publications from the Teaching Toolbox"

# Redirect to default tab
@blueprint.route("/")
def page_index():
	return redirect("tracts")

@blueprint.route("/<pub_category>")
def toolbox(pub_category):
	match pub_category:
		case "tracts":
			title = "Буклеты"
			items = Books.query.filter(Books.pub_code.like("t-3%")).order_by(Books.pub_code)
			share = lambda item: "https://www.jw.org/finder?wtlocale=U&pub=%s&srcid=share" % item.pub_code
			classes = "pubs img-crop"
		case "video":
			title = "Видео"
			items = VideoCategories.query.filter_by(subcategory_key="VODMinistryTools").one_or_none().videos
			share = lambda item: "https://www.jw.org/finder?srcid=share&wtlocale=U&lank=%s" % item.lank
			classes = "pubs"
		case "books":
			title = "Книги"
			items = Books.query.filter(Books.pub_code.in_(("lffi", "ld", "ll", "bh","bhs","lv","lvs","jl"))).order_by(Books.pub_code)
			share = lambda item: "https://www.jw.org/finder?wtlocale=U&pub=%s&srcid=share" % item.pub_code
			classes = "pubs"
		case "watchtower":
			title = "Сторожовая башня"
			items = PeriodicalIssues.query.filter_by(pub_code="wp").order_by(PeriodicalIssues.issue_code)
			share = lambda item: "https://www.jw.org/finder?wtlocale=U&issue=%s&pub=%s&srcid=share" % (item.issue_code[:4] + "-" + item.issue_code[4:], item.pub_code + item.issue_code[2:4])
			classes = "pubs"
		case "awake":
			title = "Пробудитесь!"
			items = PeriodicalIssues.query.filter_by(pub_code="g").order_by(PeriodicalIssues.issue_code)
			share = lambda item: "https://www.jw.org/finder?wtlocale=U&issue=%s&pub=%s&srcid=share" % (item.issue_code[:4] + "-" + item.issue_code[4:], item.pub_code + item.issue_code[2:4])
			classes = "pubs"
		case "invitations":
			title = "Приглашения"
			items = Books.query.filter(Books.name.like("Приглашение%")).order_by(Books.pub_code)
			share = lambda item: "https://www.jw.org/finder?wtlocale=U&pub=%s&srcid=share" % item.pub_code
			classes = "pubs"
		case _:
			title = "Invalid"
			items = []
			share = lambda item: ""
			classes = "pubs"
	return render_template("toolbox/publications.html", title=title, items=items, share=share, classes=classes)

