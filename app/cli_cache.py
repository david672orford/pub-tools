# Cache cleaner

from flask import current_app
from flask.cli import AppGroup
from collections import defaultdict
from time import time
import os, re, logging

from rich.console import Console
from rich.table import Table

from .jworg.filenames import jworg_filename_category

logger = logging.getLogger(__name__)

cli_cache = AppGroup("cache", help="Cache maintanance")

def init_app(app):
	app.cli.add_command(cli_cache)

@cli_cache.command("status", help="Show cache usage")
def cmd_cache_status():
	scan_cache()

@cli_cache.command("clean", help="Remove old files from cache")
def cmd_cache_clean():
	scan_cache(clean=True)

class Total:
	files = 0
	size = 0
	deletable_files = 0
	deletable_size = 0
	def row(self, category):
		return (
			category,
			str(self.files),
			str(int(self.size / 1048576)),
			str(self.deletable_files),
			str(int(self.deletable_size/ 1048576)),
			)

def scan_cache(clean=False):
	totals = defaultdict(Total)
	time_now = int(time())
	for entry in os.scandir(current_app.config["MEDIA_CACHEDIR"]):
		if category := jworg_filename_category(entry.name):
			if category == "song":
				category = "Songs from JW.ORG"
				lifetime = 365
			elif category == "image":
				category = "Images from JW.ORG"
				lifetime = 30
			elif category == "video":
				category = "Videos from JW.ORG"
				lifetime = 90
			else:
				raise AssertionFailed()
		elif entry.name.startswith("jwstream-"):
			category = "Clips from JW Stream"
			lifetime = 14
		elif entry.name.startswith("user-"):
			category = "User-Supplied Files"
			lifetime = 14
		elif entry.name.endswith(".epub"):
			category = "EPUB Files"
			lifetime = 365
		else:
			ext = entry.name.split(".")[-1]
			category = "Other %s Files" % ext.upper()
			lifetime = 30

		s = entry.stat()
		age = time_now - max(s.st_atime, s.st_mtime, s.st_ctime)
		deletable = age > (lifetime * 86400)

		total = totals[category]
		total.files += 1
		total.size += s.st_size
		if deletable:
			total.deletable_files += 1
			total.deletable_size += s.st_size
			if clean:
				os.unlink(entry.path)

	table = Table(show_header=True, title="Cache Use Totals")
	table.add_column("Category", style="blue")
	table.add_column("Files", justify="right")
	table.add_column("Megabytes", justify="right")
	if clean:
		table.add_column("Deleted Files", justify="right", style="red")
		table.add_column("Deleted Megabytes", justify="right", style="red")
	else:
		table.add_column("Deletable Files", justify="right", style="red")
		table.add_column("Deletable Megabytes", justify="right", style="red")
	for category, total in sorted(totals.items(), key=lambda item: item[1].size):
		table.add_row(*total.row(category))
	Console().print(table)
