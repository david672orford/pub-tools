# Whoosh search engine integration

from flask import current_app
import os, shutil

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

class VideoIndex:
	def __init__(self, index_path):
		self.index_path = index_path
		self.writer = None

	def create(self):
		# Define search index schema
		stemmer = StemmingAnalyzer(stemfn=stemfn)
		schema = Schema(
			video_id = ID(stored=True, unique=True),
			category_id = ID(stored=True, unique=True),
			content = TEXT(analyzer=stemmer),
			)

		# Delete existing index and create a new one
		if os.path.exists(self.index_path):
			shutil.rmtree(self.index_path)
		os.mkdir(self.index_path)
		create_in(self.index_path, schema)

	def add_videos(self, videos):
		if self.writer is None:
			index = open_dir(self.index_path)
			self.writer = index.writer()
		for video in videos:
			#print(video.title)
			assert video.id is not None		# can happen if record is not commited yet
			for category in video.categories:
				self.writer.update_document(
					video_id = str(int(video.id)),
					category_id = str(category.id),
					content = " ".join((category.category_name, category.subcategory_name, video.title)),
					)

	def commit(self):
		self.writer.commit()
		self.writer = None

	def search(self, q):
		deduped_results = []
		suggestion = []

		index = open_dir(self.index_path)
		with index.searcher() as searcher:

			dedup = set()
			query_obj = QueryParser("content", index.schema).parse(q)
			for hit in searcher.search(query_obj, limit=None):
				#print("hit:", hit)
				video_id = int(hit["video_id"])
				if not video_id in dedup:
					dedup.add(video_id)
					deduped_results.append((VideoCategories.query.filter_by(id=int(hit['category_id'])).one(), Videos.query.filter_by(id=video_id).one()))

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

video_index = VideoIndex(current_app.config["WHOOSH_PATH"])
