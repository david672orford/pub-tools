from app import app
from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy(app)

#=============================================================================
# Meeting dates and links to the article used at each on JW.ORG
#=============================================================================

# Workbook meeting outline and Watchtower Study article for each week
class Weeks(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	year = db.Column(db.Integer)
	week = db.Column(db.Integer)
	mwb_docid = db.Column(db.Integer)
	mwb_url = db.Column(db.String)
	watchtower_docid = db.Column(db.Integer)
	watchtower_url = db.Column(db.String)
	def week_of(self):
		return date.fromisocalendar(self.year, self.week, 1).isoformat()

#=============================================================================
# Lists of Publications and links to them on JW.ORG
#=============================================================================

# Books, brocures, tracts, invitations, etc. on JW.ORG
class Books(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	pub_code = db.Column(db.String)
	thumbnail = db.Column(db.String)
	href = db.Column(db.String)
	epub_filename = db.Column(db.String)

# PeriodicalIssues of the Watchtower, Awake!, or Meeting Workbook
class PeriodicalIssues(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	issue = db.Column(db.String)
	pub_code = db.Column(db.String)
	issue_code = db.Column(db.String)
	thumbnail = db.Column(db.String)
	href = db.Column(db.String)
	epub_filename = db.Column(db.String)
	articles = db.relationship('Articles', order_by=lambda: Articles.docid)
	def __str__(self):
		return "<PeriodicalIssues id=%d pub_code=%s issue_code=%s issue=\"%s\" href=\"%s\" epub_filename=\"%s\">" % (self.id, self.pub_code, self.issue_code, self.issue, self.href, self.epub_filename)

# Articles from the Watchtower or the Meeting Workbook
class Articles(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	issue_id = db.Column(db.Integer, db.ForeignKey('periodical_issues.id'))
	issue = db.relationship(PeriodicalIssues, back_populates="articles")
	docid = db.Column(db.String)
	title = db.Column(db.String)
	thumbnail = db.Column(db.String)
	href = db.Column(db.String)
	epub_href = db.Column(db.String)

#=============================================================================
# Videos on JW.ORG
#=============================================================================

videos_rel = db.Table("videos_rel", db.Model.metadata,
    db.Column('category_id', db.Integer, db.ForeignKey('video_categories.id'), primary_key=True),
    db.Column('video_id', db.Integer, db.ForeignKey('videos.id'), primary_key=True)
    )

class VideoCategories(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	category_key = db.Column(db.String)
	category_name = db.Column(db.String)
	subcategory_key = db.Column(db.String)
	subcategory_name = db.Column(db.String)
	videos = db.relationship('Videos', secondary=videos_rel, back_populates="categories") #, lazy="dynamic")

class Videos(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	lank = db.Column(db.String)				# language agnostic natural key
	date = db.Column(db.DateTime)
	docid = db.Column(db.String)			# MEPS document ID
	thumbnail = db.Column(db.String)
	href = db.Column(db.String)				# finder link
	categories = db.relationship(VideoCategories, secondary=videos_rel, back_populates="videos")

db.create_all()
