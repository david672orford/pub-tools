"""Get theme, possibly matching that of OBS"""

from flask import current_app

class Theme:
	def __init__(self):
		self.default = theme = current_app.config.get("THEME")
		if self.default is None:
			self.default = "yami-light"
		self.name = None
	def set(self, name:str) -> None:
		assert type(name) is str
		self.name = name
	@property
	def stylesheet(self) -> str:
		name = self.name or self.default
		assert type(name) is str
		return "themes/" + name + "/theme.css"

