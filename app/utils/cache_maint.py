from collections import defaultdict
from time import time
import os
import re

from flask import current_app
from rich.console import Console
from rich.table import Table

from ..jworg.filenames import jworg_filename_category

def scan_cache(clean=False, print_summary_table=True):
	totals = Totals(clean)
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
				lifetime = 30
			elif category == "pdf":
				category = "PDF files from JW.ORG"
				lifetime = 30
			else:
				raise AssertionError(f"No case for {category}")
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
			print(entry.name)
			category = "Other %s Files" % ext.upper()
			lifetime = 30

		totals.add(entry, category, lifetime)

	for entry in os.scandir(current_app.config["GDRIVE_CACHEDIR"]):
		totals.add(entry, "Gdrive Cache", lifetime=90)

	for entry in os.scandir(current_app.config["FLASK_CACHEDIR"]):
		totals.add(entry, "Flask Cache", lifetime=1)

	if print_summary_table:
		totals.print_summary_table()

class Totals:
	"""Counts of files and space used, deletable by category. Optionally delete."""

	def __init__(self, clean):
		self.clean = clean
		self.time_now = int(time())
		self.totals = defaultdict(Total)

	def add(self, entry, category, lifetime):
		if self.totals[category].add(entry, self.time_now, lifetime) and self.clean:
			os.unlink(entry.path)

	def print_summary_table(self):
		table = Table(show_header=True, title="Cache Use Totals")
		table.add_column("Category", style="blue")
		table.add_column("Files", justify="right")
		table.add_column("Megabytes", justify="right")
		if self.clean:
			table.add_column("Deleted Files", justify="right", style="red")
			table.add_column("Deleted Megabytes", justify="right", style="red")
		else:
			table.add_column("Deletable Files", justify="right", style="red")
			table.add_column("Deletable Megabytes", justify="right", style="red")
		for category, total in sorted(self.totals.items(), key=lambda item: item[1].size):
			table.add_row(*total.row(category))
		Console().print(table)

class Total:
	"""Counts of files and space used, deletable for a category. Optionally delete."""

	files = 0
	size = 0
	deletable_files = 0
	deletable_size = 0

	def add(self, entry, time_now, lifetime):

		# Compare the age of the file to the lifetime for this category
		s = entry.stat()
		age = time_now - max(s.st_atime, s.st_mtime, s.st_ctime)
		deletable = age > (lifetime * 86400)

		self.files += 1
		self.size += s.st_size
		if deletable:
			self.deletable_files += 1
			self.deletable_size += s.st_size
		return deletable

	def row(self, category):
		return (
			category,
			str(self.files),
			str(int(self.size / 1048576)),
			str(self.deletable_files),
			str(int(self.deletable_size/ 1048576)),
			)
