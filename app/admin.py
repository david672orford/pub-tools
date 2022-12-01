from flask_admin import Admin
from flask_admin.contrib.sqla.view import ModelView as InsecureModelView
from flask_admin.form import SecureForm

from .models import db, Weeks, PeriodicalIssues, Articles, Books, VideoCategories, Videos

admin = Admin()

def init_app(app):
	admin.name = app.config['APP_DISPLAY_NAME']
	admin.init_app(app)

# Create base model view
class ModelView(InsecureModelView):
    form_base_class = SecureForm
    page_size = 15

class WeeksView(ModelView):
	pass

class PeriodicalIssuesView(ModelView):
	pass

class ArticlesView(ModelView):
	pass

class BooksView(ModelView):
	pass

class VideoCategoriesView(ModelView):
	pass

class VideosView(ModelView):
	pass

admin.add_view(WeeksView(Weeks, db.session))
admin.add_view(PeriodicalIssuesView(PeriodicalIssues, db.session))
admin.add_view(ArticlesView(Articles, db.session))
admin.add_view(BooksView(Books, db.session))
admin.add_view(VideoCategoriesView(VideoCategories, db.session))
admin.add_view(VideosView(Videos, db.session))

