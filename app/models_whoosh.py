# Whoosh search engine integration

from flask import current_app
import warnings
import os

# https://whoosh.readthedocs.io/en/latest/
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, ID, TEXT
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser

from .models import VideoCategories, Videos

# Dictionary-based stemmer for Russian
def morpher():
	if not hasattr(morpher, "obj"):
		import pymorphy2
		morpher.obj = pymorphy2.MorphAnalyzer()
	return morpher.obj

# Stemmer function for Whoosh which pickels a reference to it
def stemfn(word):
	return morpher().parse(word)[0].normal_form

class BaseWhooshIndex:
	def __init__(self, whoosh_path):
		self.whoosh_path = whoosh_path
		self._writer = None

	def create(self):
		if not os.path.exists(self.whoosh_path):
			os.mkdir(self.whoosh_path)

		# Create the index or clear it if it already exists
		create_in(self.whoosh_path, self.schema, indexname=self.indexname)

	def open(self):
		with warnings.catch_warnings():
			# See https://github.com/mchaput/whoosh/commit/d9a3fa2a4905e7326c9623c89e6395713c189161
			warnings.simplefilter("ignore", category=SyntaxWarning)
			index = open_dir(self.whoosh_path, indexname=self.indexname)
		return index

	@property
	def writer(self):
		if self._writer is None:
			self._writer = open_dir(self.whoosh_path, indexname=self.indexname).writer()
		return self._writer

	def commit(self):
		self._writer.commit()
		self._writer = None

class VideoIndex(BaseWhooshIndex):
	indexname = "videos"
	schema = Schema(
		video_id = ID(stored=True, unique=True),
		category_id = ID(stored=True, unique=True),
		content = TEXT(analyzer=StemmingAnalyzer(stemfn=stemfn)),
		)

	def add_videos(self, videos):
		with warnings.catch_warnings():
			warnings.simplefilter("ignore", category=SyntaxWarning)
			for video in videos:
				#print(video.title)
				assert video.id is not None		# can happen if record is not commited yet
				for category in video.categories:
					self.writer.update_document(
						video_id = str(int(video.id)),
						category_id = str(category.id),
						content = " ".join((category.category_name, category.subcategory_name, video.title)),
						)

	def search(self, q:str):
		deduped_results = []
		suggestion = []

		index = self.open()
		with index.searcher() as searcher:

			dedup = set()
			query_obj = QueryParser("content", index.schema).parse(q)
			for hit in searcher.search(query_obj, limit=None):
				#print("hit:", hit)
				video_id = int(hit["video_id"])
				if not video_id in dedup:
					dedup.add(video_id)
					deduped_results.append((
						VideoCategories.query.filter_by(id=int(hit["category_id"])).one(),
						Videos.query.filter_by(id=video_id).one()
						))

			if len(deduped_results) < 10:
				corrector = searcher.corrector("content")
				changes = 0
				preliminary_suggestion = []
				for word in q.split():
					dict_entry = morpher().parse(word)[0]
					if not dict_entry.is_known:
						alternatives = corrector.suggest(word, limit=1)
						if len(alternatives) > 0 and alternatives[0] != dict_entry.normal_form:
							preliminary_suggestion.append(alternatives[0])
						else:
							pass		# drop the word
						changes += 1
						continue
					preliminary_suggestion.append(word)
				if changes > 0:
					suggestion = preliminary_suggestion

		return deduped_results, " ".join(suggestion)

class IllustrationIndex(BaseWhooshIndex):
	indexname = "illustrations"
	schema = Schema(
		pub_code = ID(stored=True, unique=True),
		src = ID(stored=True, unique=True),
		caption = TEXT(stored=True),
		alt = TEXT(stored=True),
		content = TEXT(analyzer=StemmingAnalyzer(stemfn=stemfn)),
		)

	def add_illustration(self, pub_code:str, src:str, caption:str, alt:str):
		self.writer.update_document(
			pub_code = pub_code,
			src = src,
			caption = caption,
			alt = alt,
			content = " ".join((caption, alt)),
			)

	def search(self, q:str):
		index = self.open()
		with index.searcher() as searcher:
			query_obj = QueryParser("content", index.schema).parse(q)
			hits = searcher.search(query_obj, limit=None)
			for hit in hits:
				hit.excerpt = hit.highlights("content", text=" ".join((hit["caption"], hit["alt"])), top=3)
				yield hit

	def get_document(self, docnum:int):
		index = self.open()
		with index.searcher() as searcher:
			return searcher.stored_fields(docnum)

config = current_app.config
whoosh_path = config["WHOOSH_PATH"] + "-" + config["PUB_LANGUAGE"]
video_index = VideoIndex(whoosh_path)
illustration_index = IllustrationIndex(whoosh_path)
