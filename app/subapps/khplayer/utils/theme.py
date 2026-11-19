"""Get theme, possibly matching that of OBS"""

from flask import current_app

class Theme:
	def __init__(self):
		self.default:str
		self.name:str|None = None
		theme = current_app.config.get("THEME")
		if type(theme) is str:
			self.default = theme
		else:
			self.default = "yami-light"
	def set(self, name:str) -> None:
		assert type(name) is str
		self.name = name
	@property
	def stylesheet(self) -> str:
		name = self.name or self.default
		assert type(name) is str
		return "themes/" + name + "/theme.css"
