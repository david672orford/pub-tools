class NoWidget(Exception):
	pass

class ZoomControl:
	def __init__(self):
		self.sharing = False
	def is_sharing(self):
		return self.sharing
	def open_sharing_dialog(self, hide=False):
		pass
	def start_screensharing(self):
		self.sharing = True
	def stop_screensharing(self):
		self.sharing = False

