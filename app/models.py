from app import app

db = SQLAlchemy(app)

class Publications(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String)
	issue = db.Column(db.String)
	code = db.Column(db.String)
	issue_code = db.Column(db.String)
	href = db.Column(db.String)
	thumbnail = db.Column(db.String)

db.session.create()

