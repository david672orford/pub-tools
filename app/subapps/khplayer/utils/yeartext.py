from datetime import date
from zipfile import ZipFile
import re
from time import sleep
import sys

from flask import current_app
from icecream import ic

from .controllers import obs, ObsError
from ....jworg.publications import PubFinder
from ....jworg.epub import EpubLoader
from ....utils.babel import gettext as _
from .httpfile import HttpFile

def create_yeartext_scene():
	yeartext = get_yeartext()
	lines = split_yeartext(yeartext)
	return create_text_scene(lines)

def get_yeartext():
	"""Download the January Watchtower (Study Edition) and extract yeartext"""
	year = date.today().year
	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])
	epub_url = pub_finder.get_epub_url("w", f"{year}01")
	fh = HttpFile(epub_url, debug=False)
	zipfh = ZipFile(fh)
	epub = EpubLoader(zipfh)
	#print("\n".join(map(str, epub.opf.toc)))
	xml = epub.load_html(epub.opf.toc[0].href)
	return xml.xpath(".//p[@id='p6']")[0].text_content()

def split_yeartext(yeartext):
	m = re.match(r"^(.+)\s+(\([^\)]+\)\.?)$", yeartext)
	text, cite = m.groups()
	center = int(len(text) / 2)
	left_space = text.rindex(" ", 0, center)
	left_cost = (center - left_space) * 1.5		# looks worse
	right_space = text.index(" ", center)
	right_cost = (right_space - center)
	#ic(text, len(text), center, left_space, right_space, left_cost, right_cost)
	if left_cost < right_cost:
		return text[:left_space], text[left_space+1:], cite
	else:
		return text[:right_space], text[right_space+1:], cite

def create_text_scene(lines):
	frame_width = 1280
	frame_height = 720

	logo_size = 110
	logo_margin = 70
	logo_x = frame_width - logo_size - logo_margin
	logo_y = frame_height - logo_size - logo_margin
	logo_text_shift = 10

	# FIXME: Can we check what fonts are installed? It should be
	# possible to enumerate them as input options.
	if sys.platform == "linux":
		text_font = {
			"face": "Liberation Serif",
			"style": "Bold",
			"size": 48,
			}
		logo_font = {
			"face": "Roboto Condensed",
			"style": "Regular",
			"size": 72,
			}
	else:
		text_font = {
			"face": "Times New Roman",
			"style": "Regular",
			"size": 55,
			}
		logo_font = {
			"face": "Arial",
			"style": "Regular",
			"size": 65,
			}
	text_line_spacing = text_font["size"] * 1.5

	try:
		scene_uuid = obs.create_scene(_("* Yeartext"))["sceneUuid"]
	except ObsError as e:
		if e.code == 601:
			return False
		raise

	seq = 1
	y = (frame_height - (len(lines) * text_line_spacing)) / 2
	for line in lines:
		result = obs.create_unique_input(
			scene_uuid = scene_uuid,
			input_name = f"Yeartext Line {seq}",
			input_kind = "text_ft2_source_v2",
			input_settings = {
				"font": text_font,
				"text": line,
				}
			)
		sleep(0.5)
		xform = obs.get_scene_item_transform(scene_uuid=scene_uuid, scene_item_id=result["sceneItemId"])
		obs.set_scene_item_transform(scene_uuid, result["sceneItemId"], {
			"positionX": (frame_width - xform["width"]) / 2,
			"positionY": y,
			})
		seq += 1
		y += text_line_spacing

	# JW Logo Background
	result = obs.create_unique_input(
		scene_uuid = scene_uuid,
		input_name = "JW Logo Background",
		input_kind = "color_source_v3",
		input_settings = {
			"color": 436207615,		# 10% gray
			"height": logo_size,
			"width": logo_size,
			}
		)
	obs.set_scene_item_transform(scene_uuid, result["sceneItemId"], {
		"positionX": logo_x,
		"positionY": logo_y,
		})

	# JW Logo Lettering
	result = obs.create_unique_input(
		scene_uuid = scene_uuid,
		input_name = "JW Logo",
		input_kind = "text_ft2_source_v2",
		input_settings = {
			"color1": 4278190080,		# black
			"color2": 4278190080,
			"font": logo_font,
			"text": "JW",
			}
		)
	sleep(0.5)
	xform = obs.get_scene_item_transform(scene_uuid=scene_uuid, scene_item_id=result["sceneItemId"])
	obs.set_scene_item_transform(scene_uuid, result["sceneItemId"], {
		"positionX": logo_x + ((logo_size - xform["width"]) / 2),
		"positionY": logo_y + ((logo_size - xform["height"]) / 2) - logo_text_shift,
		})

	return True
