from flask import current_app
import os, shutil
import pymorphy2

# https://whoosh.readthedocs.io/en/latest/
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, ID, TEXT
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import QueryParser

from .models import VideoCategories, Videos

# Dictionary-based stemmer for Russian
# Thus function must be defined at the module level because Whoosh
# pickles a call to it.
morph = pymorphy2.MorphAnalyzer()
def stemfn(word):
	return morph.parse(word)[0].normal_form

def update_video_index():

	# Define search index schema
	stemmer = StemmingAnalyzer(stemfn=stemfn)
	schema = Schema(
		video_id = ID(stored=True),
		category_id = ID(stored=True),
		content = TEXT(analyzer=stemmer),
		)

	index_path = current_app.config["WHOOSH_PATH"]
	if os.path.exists(index_path):
		shutil.rmtree(index_path)
	os.mkdir(index_path)
	ix = create_in(index_path, schema)
	writer = ix.writer()

	for video in Videos.query:
		#print(video.name)
		for category in video.categories:
			writer.add_document(
				video_id = str(video.id),
				category_id = str(category.id),
				content = " ".join((category.category_name, category.subcategory_name, video.name)),
				)	

	writer.commit()

def video_search(q):
	deduped_results = []
	suggestion = []

	ix = open_dir(current_app.config["WHOOSH_PATH"])
	with ix.searcher() as searcher:

		dedup = set()
		query_obj = QueryParser("content", ix.schema).parse(q)
		for hit in searcher.search(query_obj, limit=None):
			video_id = int(hit["video_id"])
			if not video_id in dedup:
				dedup.add(video_id)
				deduped_results.append((VideoCategories.query.filter_by(id=int(hit['category_id'])).one(), Videos.query.filter_by(id=video_id).one()))

		if len(deduped_results) < 10:
			corrector = searcher.corrector("content")
			changes = 0
			preliminary_suggestion = []
			for word in q.split():
				dict_entry = morph.parse(word)[0]
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

