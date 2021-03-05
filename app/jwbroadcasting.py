from jwfetcher import Fetcher
from urllib.parse import urlencode
import re

class VideoCategory(Fetcher):
	mediator_url = 'https://data.jw-api.org/mediator/v1/categories/{language}/{category}?detailed=1&clientType=www'
	language = 'U'	# U is Russian

	def __init__(self, category_key, category_dict=None):
		super().__init__()

		if category_dict is None or len(category_dict['media']) == 0:
			data = self.get_json(self.mediator_url.format(language=self.language, category=category_key))
			category_dict = data['category']
			#self.dump_json(category_dict)

		self.key = category_dict['key']
		self.name = category_dict['name']
		#print(self.key, self.name)

		self.videos = []
		for media in category_dict.get('media',[]):
			#self.dump_json(media)
			self.videos.append(Video(self, media))

		self.subcategories = []
		for subcategory in category_dict.get('subcategories',[]):
			self.subcategories.append(VideoCategory(subcategory['key'], category_dict = subcategory))

		# We believe a category can contain videos or subcategories, but not both.
		assert len(self.videos) == 0 or len(self.subcategories) == 0

class Video:
	finder_url = 'https://www.jw.org/finder'
	def __init__(self, category_obj, media):
		self.name = media['title']
		self.code = media['naturalKey']
		try:
			self.thumbnail = media['images']['wss']['sm']		# 16:9, occassionally missing
		except KeyError:
			self.thumbnail = media['images']['lss']['lg']		# 2:1

		self.href = self.finder_url + "?" + urlencode(dict(lank=media['languageAgnosticNaturalKey'], wtlocale=category_obj.language))
		self.files = {}
		for file in media['files']:
			self.files[file['label']] = file['progressiveDownloadURL']

if __name__ == "__main__":
	def print_videos(category, indent=0):
		print("%s%s (%s)" % (" " * indent, category.name, category.key))
		for video in category.videos:
			print("%s%s" % (" " * (indent+2), video.name))
		for subcategory in category.subcategories:
			print_videos(subcategory, indent=indent + 4)
	
	#category = VideoCategory("VideoOnDemand")
	category = VideoCategory("VODMinistryTools")

	print_videos(category)


