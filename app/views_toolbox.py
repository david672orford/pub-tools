from flask import render_template
from . import app
from .models import Issues, Books, Videos

@app.route("/")
def toolbox():
	return render_template("toolbox/publications.html", categories=[
		#("Приглашения", Publications.query.filter(Publications.name.like("Приглашение%")).order_by(Publications.code)),
		("Видио", Videos.query.filter_by(category="VODMinistryTools").order_by(Videos.code)),
		("Книги", Books.query.filter(Books.code.in_(("lffi", "ld", "ll", "bh","bhs","lv","lvs","jl"))).order_by(Publications.code)),
		#("Буклеты", Publications.query.filter(Publications.code.like("t-3%")).order_by(Publications.code)),
		("Сторожевая башня", Issues.query.filter_by(code="wp").order_by(Issues.issue_code)),
		("Пробудуйтесь!", Issues.query.filter_by(code="g").order_by(Issues.issue_code))
		])

@app.route("/рабочая-тетрадь")
def workbook():
	return render_template("toolbox/publications.html", categories=[
		("Рабочая тетрадь", Issues.query.filter_by(code="mwb").order_by(Issues.issue_code))
		])


@app.route("/видеоролики")
def videos():
	return render_template("toolbox/videos.html", videos=Videos.query.order_by(Videos.category, Videos.subcategory, Videos.name))

