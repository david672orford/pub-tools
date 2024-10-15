# Flask-Admin access to the database

from flask_admin import Admin
from flask_admin.contrib.sqla.view import ModelView as InsecureModelView
from flask_admin.form import SecureForm

from ...models import db, Weeks, MeetingCache, PeriodicalIssues, Articles, Books, VideoCategories, Videos, Config
from .custom_formatters import format_json

admin = Admin()

# Create base model view
class ModelView(InsecureModelView):
    form_base_class = SecureForm
    page_size = 15

class ConfigView(ModelView):
	pass

class WeeksView(ModelView):
	pass

class MeetingCacheView(ModelView):
	column_formatters = {
		"media": format_json,
		}

class PeriodicalIssuesView(ModelView):
	pass

class ArticlesView(ModelView):
	pass

class BooksView(ModelView):
	pass

class VideoCategoriesView(ModelView):
	column_filters = ("lang", "category_key", "subcategory_key")

class VideosView(ModelView):
	column_list = (
		"lang",
		"categories",
		"title",
		"date",
		"duration",
		"lank"
		"docid",
		"thumbnail",
		"href",
		)
	column_searchable_list = ("title", "lank")

admin.add_view(ConfigView(Config, db.session))
admin.add_view(WeeksView(Weeks, db.session))
admin.add_view(MeetingCacheView(MeetingCache, db.session))
admin.add_view(PeriodicalIssuesView(PeriodicalIssues, db.session))
admin.add_view(ArticlesView(Articles, db.session))
admin.add_view(BooksView(Books, db.session))
admin.add_view(VideoCategoriesView(VideoCategories, db.session))
admin.add_view(VideosView(Videos, db.session))

