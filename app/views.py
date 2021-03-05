from flask import render_template
from . import app
from .models import Publications, Videos

@app.route("/все")
def all_pubs():
	return render_template("publications.html", categories=[
		("все", Publications.query.order_by(Publications.code, Publications.issue_code))
		])

@app.route("/")
def toolbox():
	return render_template("publications.html", categories=[
		("Приглашения", Publications.query.filter(Publications.name.like("Приглашение%")).order_by(Publications.code)),
		("Видио", Videos.query.filter_by(category="VODMinistryTools").order_by(Videos.code)),
		("Книги", Publications.query.filter(Publications.code.in_(("lffi", "ld", "ll", "bh","bhs","lv","lvs","jl"))).order_by(Publications.code)),
		("Буклеты", Publications.query.filter(Publications.code.like("t-3%")).order_by(Publications.code)),
		("Сторожевая башня", Publications.query.filter_by(code="wp").order_by(Publications.issue_code)),
		("Пробудуйтесь!", Publications.query.filter_by(code="g").order_by(Publications.issue_code))
		])

@app.route("/рабочая-тетрадь")
def workbook():
	return render_template("publications.html", categories=[
		("Рабочая тетрадь", Publications.query.filter_by(code="mwb").order_by(Publications.issue_code))
		])


@app.route("/видеоролики")
def videos():
	return render_template("videos.html", videos=Videos.query.order_by(Videos.category, Videos.subcategory, Videos.name))

