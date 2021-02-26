from flask import render_template
from . import app
from .models import Publications

@app.route("/")
def index():
	return render_template("publications.html", categories=[
		("все", Publications.query.order_by(Publications.code, Publications.issue_code))
		])

@app.route("/toolbox")
def toolbox():
	return render_template("publications.html", categories=[
		("Приглашения", Publications.query.filter(Publications.name.like("Приглашение%")).order_by(Publications.code)),
		("Видио", Publications.query.filter(Publications.code.like("%_VIDEO")).order_by(Publications.code)),
		("Книги", Publications.query.filter(Publications.code.in_(("ld", "ll", "bh","bhs","lv","lvs","jl"))).order_by(Publications.code)),
		("Буклеты", Publications.query.filter(Publications.code.like("t-3%")).order_by(Publications.code)),
		("Сторожевая башня", Publications.query.filter_by(code="wp").order_by(Publications.issue_code)),
		("Пробудуйтесь!", Publications.query.filter_by(code="g").order_by(Publications.issue_code))
		])

