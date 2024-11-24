"""
CLI for the Zoom tracker
"""

from flask.cli import AppGroup
import click

from PIL import Image

from .utils.zoom_tracker import zoom_tracker, ZoomBoxFinder

cli_zoom = AppGroup("zoom", help="Zoom scene control")

@cli_zoom.command("track")
def cmd_zoom_track():
	"""Track current speaker in Zoom window"""
	zoom_tracker()

@cli_zoom.command("test")
@click.argument("filename")
def cmd_zoom_test(filename):
	"""Test the Zoom box finder"""

	finder = ZoomBoxFinder()
	img = Image.open(filename)
	finder.load_image(img)

	print("Gallery:", finder.gallery)
	finder.draw_box(finder.gallery)

	print("Speaker size:", finder.speaker.width, finder.speaker.height)
	finder.draw_box(finder.speaker)

	print("Speaker index:", finder.speaker_indexes[0])

	for crop in finder.layout:
		finder.draw_box(crop)

	finder.img.show()
