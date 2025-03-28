from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

def init_app(app):
	db.init_app(app)
	db.create_all()

class Config(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String, nullable=False, unique=True)
	data = db.Column(db.JSON)
	def __str__(self):
		return "<Config name=%s data=%s>" % (self.name, self.data)

#=============================================================================
# Meeting dates and links to the article used at each on JW.ORG
#=============================================================================

# Workbook meeting outline and Watchtower Study article for each week
class Weeks(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	year = db.Column(db.Integer)
	week = db.Column(db.Integer)
	mwb_docid = db.Column(db.Integer)
	watchtower_docid = db.Column(db.Integer)
	def week_of(self):
		return date.fromisocalendar(self.year, self.week, 1).isoformat()

class MeetingCache(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(db.String)
	docid = db.Column(db.Integer)		# Watchtower or Workbook article
	media = db.Column(db.JSON)			# Extracted media list

#=============================================================================
# Lists of Publications and links to them on JW.ORG
#=============================================================================

# Books, brocures, tracts, invitations, etc. on JW.ORG
class Books(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(db.String)
	name = db.Column(db.String)
	pub_code = db.Column(db.String)
	href = db.Column(db.String)
	thumbnail = db.Column(db.String)
	formats = db.Column(db.String)
	epub_filename = db.Column(db.String)

# PeriodicalIssues of the Watchtower, Awake!, or Meeting Workbook
class PeriodicalIssues(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(db.String)
	name = db.Column(db.String)
	issue = db.Column(db.String)
	pub_code = db.Column(db.String)
	issue_code = db.Column(db.String)
	href = db.Column(db.String)
	thumbnail = db.Column(db.String)
	formats = db.Column(db.String)
	epub_filename = db.Column(db.String)
	articles = db.relationship("Articles", order_by=lambda: Articles.docid)
	def __str__(self):
		return "<PeriodicalIssues id=%d pub_code=%s issue_code=%s issue=\"%s\" href=\"%s\" epub_filename=\"%s\">" % (self.id, self.pub_code, self.issue_code, self.issue, self.href, self.epub_filename)

# Articles from the Watchtower or the Meeting Workbook
class Articles(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(db.String)
	issue_id = db.Column(db.Integer, db.ForeignKey("periodical_issues.id"))
	issue = db.relationship(PeriodicalIssues, back_populates="articles")
	docid = db.Column(db.String)
	title = db.Column(db.String)
	href = db.Column(db.String)
	thumbnail = db.Column(db.String)
	epub_href = db.Column(db.String)

#=============================================================================
# Videos on JW.ORG
#=============================================================================

# A video can be in multiple categories, so we need a third table to connect them.
videos_rel = db.Table("videos_rel", db.Model.metadata,
    db.Column("category_id", db.Integer, db.ForeignKey("video_categories.id"), primary_key=True),
    db.Column("video_id", db.Integer, db.ForeignKey("videos.id"), primary_key=True)
    )

class VideoCategories(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(db.String)
	category_key = db.Column(db.String)
	category_name = db.Column(db.String)
	subcategory_key = db.Column(db.String)
	subcategory_name = db.Column(db.String)
	videos = db.relationship("Videos", secondary=videos_rel, back_populates="categories") #, lazy="dynamic")
	def __str__(self):
		return f"<VideoCategories id={self.id} {repr(self.category_key)} {repr(self.subcategory_name)}>"

class Videos(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	lang = db.Column(db.String)				# ISO language code
	title = db.Column(db.String)			# name of video
	date = db.Column(db.DateTime)
	duration = db.Column(db.Integer)		# running time in seconds
	lank = db.Column(db.String)				# language agnostic natural key
	docid = db.Column(db.String)			# MEPS document ID
	thumbnail = db.Column(db.String)		# URL of JPEG file
	href = db.Column(db.String)				# finder link
	categories = db.relationship(VideoCategories, secondary=videos_rel, back_populates="videos")

