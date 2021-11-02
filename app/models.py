from app import app
from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy(app)

# Workbook meeting outline and Watchtower Study article for each week
class Weeks(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	year = db.Column(db.Integer)
	week = db.Column(db.Integer)
	mwb_docid = db.Column(db.Integer)
	watchtower_docid = db.Column(db.Integer)
	def week_of(self):
		return date.fromisocalendar(self.year, self.week, 1).isoformat()

# Issues of the Watchtower or Meeting Workbook
class Issues(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	pub_code = db.Column(db.String)
	issue_code = db.Column(db.String)
	issue = db.Column(db.String)
	href = db.Column(db.String)
	epub_filename = db.Column(db.String)
	articles = db.relationship('Articles', order_by=lambda: Articles.docid)
	def __str__(self):
		return "<Issues id=%d pub_code=%s issue_code=%s issue=\"%s\" href=\"%s\" epub_filename=\"%s\">" % (self.id, self.pub_code, self.issue_code, self.issue, self.href, self.epub_filename)

# Articles from the Watchtower or the Meeting Workbook
class Articles(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'))
	issue = db.relationship(Issues)
	docid = db.Column(db.String)
	title = db.Column(db.String)
	href = db.Column(db.String)
	epub_href = db.Column(db.String)

# Videos on JW.ORG
class Videos(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	category = db.Column(db.String)
	subcategory = db.Column(db.String)
	name = db.Column(db.String)
	lank = db.Column(db.String)				# language agnostic natural key
	docid = db.Column(db.String)			# MEPS document ID
	href = db.Column(db.String)				# finder link
	thumbnail = db.Column(db.String)

# Books, brocures, etc. on JW.ORG
class Books(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	pub_code = db.Column(db.String)
	href = db.Column(db.String)
	epub_filename = db.Column(db.String)

db.create_all()
