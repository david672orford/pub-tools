from .fetcher import Fetcher
from urllib.parse import urlencode
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Retrieve a video category from JW.ORG. Returns a VideoCategory object.
class VideoLister(Fetcher):
	def get_category(self, category_key, category_dict=None):
		logger.debug("get_category(\"%s\", %s)", category_key, category_dict)
		if category_dict is None or len(category_dict['media']) == 0:
			data = self.get_json(self.mediator_categories_url.format(meps_language=self.meps_language, category=category_key))
			category_dict = data['category']
		return VideoCategory(self, category_dict)

# The contents of a video category from JW.ORG. Members:
# .videos -- a list of Video objects representing the videos in this category
# .subcategories -- a list of VideoCategory objects representing the subcategories
#                   in this category
# A VideoCategory will have either videos or subcategories, but not both.
class VideoCategory:
	def __init__(self, video_lister, category_dict):
		self.video_lister = video_lister
		self.category_dict = category_dict

		self.meps_language = video_lister.meps_language
		self.key = category_dict['key']
		self.name = category_dict['name']
		self.subcategories_count = len(category_dict.get('subcategories',[]))

		self.videos = []
		for media in category_dict.get('media',[]):
			logger.debug("Video title: %s", media['title'])
			self.videos.append(Video(video_lister.meps_language, media))

		# As we understand it a category can contain videos or it can contain subcategories, but not both.
		assert len(self.videos) == 0 or len(category_dict.get('subcategories',[])) == 0

	@property
	def subcategories(self):
		for subcategory_dict in self.category_dict.get('subcategories',[]):
			logger.debug("Subcategory name: %s", subcategory_dict['name'])
			yield self.video_lister.get_category(subcategory_dict['key'], category_dict=subcategory_dict)

	@property
	def language(self):
		return self.video_lister.language

# A single video from JW.ORG
class Video:
	finder_url = 'https://www.jw.org/finder'
	def __init__(self, language, media):
		self.title = media['title']
		self.date = datetime.fromisoformat(media['firstPublished'][:-1])	# cut off Z
		self.duration = int(media["duration"] + 0.5)
		self.lank = media['languageAgnosticNaturalKey']

		try:
			self.thumbnail = media['images']['wss']['sm']		# 16:9 aspect ratio, occassionally missing
		except KeyError:
			self.thumbnail = media['images']['lss']['lg']		# 2:1 aspect ratio

		# Shareable link to the video player page
		self.href = self.finder_url + "?" + urlencode(dict(lank=self.lank, wtlocale=language))

		#self.files = {}
		#for file in media['files']:
		#	self.files[file['label']] = file['progressiveDownloadURL']

if __name__ == "__main__":
	def print_videos(category, indent=0):
		print("%s%s (%s)" % (" " * indent, category.name, category.key))
		for video in category.videos:
			print("%s%s" % (" " * (indent+2), video.title))
		for subcategory in category.subcategories:
			print_videos(subcategory, indent=indent + 4)

	logging.basicConfig(level=logging.DEBUG)

	video_lister = VideoLister()	
	category = video_lister.get_category("VideoOnDemand")
	#category = video_lister.get_category("VODMinistryTools")

	print_videos(category)

