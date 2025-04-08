"""
CLI for slides
"""

import os

from flask import current_app
from flask.cli import AppGroup
import click
from rich.console import Console
from rich.table import Table

from .utils.localdrive import LocalDriveClient
from .utils.httpfile import LocalZip
from .utils.playlists import ZippedPlaylist

cli_slides = AppGroup("slides", help="Test Slides backends")

@cli_slides.command("playlist")
@click.option("--debuglevel", type=int, default=0)
@click.argument("path_items", nargs=-1)
def slides_playlist(debuglevel, path_items):
	"""Read a playlist from a local zip file"""

	slides_dir = current_app.config["SLIDES_DIR"]

	break_point = None
	for i in range(len(path_items)):
		path = os.path.join(slides_dir, *path_items[:i+1])
		if os.path.isfile(path):
			break_point = i
			break

	if break_point is not None:
		zip_filename = os.path.join(slides_dir, *path_items[:break_point+1])
		client = ZippedPlaylist(
			(slides_dir,) + path_items[:break_point+1],
			path_items[break_point+1:],
			zip_reader = LocalZip(zip_filename),
			zip_filename = zip_filename,
			client_class = LocalDriveClient,
			debuglevel = debuglevel,
			)
	else:
		client = LocalDriveClient((slides_dir,) + path_items, [])

	table = Table(show_header=True, title="Playlist Folders", show_lines=False)
	table.add_column("ID")
	table.add_column("Title")
	for folder in client.list_folders():
		table.add_row(str(folder.id), folder.title)
	Console().print(table)

	table = Table(show_header=True, title="Playlist Media", show_lines=False)
	table.add_column("ID")
	table.add_column("Title")
	table.add_column("Filename")
	table.add_column("File Size")
	for image_file in client.list_image_files():
		table.add_row(str(image_file.id), image_file.title, image_file.filename, str(image_file.file_size))
	Console().print(table)
