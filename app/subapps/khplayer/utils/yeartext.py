from datetime import date
from flask import current_app

from .controllers import obs, ObsError
from ....jworg.publications import PubFinder

def get_yeartext():
	year = date.today().year
	print("year:", year)
	pub_finder = PubFinder(language=current_app.config["PUB_LANGUAGE"])
	for pub in pub_finder.search("magazines/", {
		"pubFilter": "wp",
		"contentLanguageFilter": pub_finder.language,
		"yearFilter": str(year),
		}):
		print(pub)

def create_yeartext_scene(lines):
	frame_width = 1280
	frame_height = 720
	logo_size = 110
	logo_margin = 70
	logo_x = frame_width - logo_size - logo_margin
	logo_y = frame_height - logo_size - logo_margin
	text_font_size = 48
	text_line_spacing = 48 * 1.5
	lines = lines.split("\n")

	scene_uuid = obs.create_scene(_("* Yeartext"))["sceneUuid"]

	seq = 1
	y = (frame_height - (len(lines) * text_line_spacing)) / 2
	for line in lines:
		result = obs.create_unique_input(
			scene_uuid = scene_uuid,
			input_name = f"Yeartext Line {seq}",
			input_kind = "text_ft2_source_v2",
			input_settings = {
				"font": {
					"face": "Liberation Serif",
					"style": "Bold",
					"size": text_font_size,
					},
				"text": line,
				}
			)
		xform = obs.get_scene_item_transform(scene_uuid=scene_uuid, scene_item_id=result["sceneItemId"])
		sleep(0.5)
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

	# JW Logo
	result = obs.create_unique_input(
		scene_uuid = scene_uuid,
		input_name = "JW Logo",
		input_kind = "text_ft2_source_v2",
		input_settings = {
			"color1": 4278190080,		# black
			"color2": 4278190080,
			"font": {
				"face": "Roboto Condensed",
				"style": "Regular",
				"size": 72,
				},
			"text": "JW",
			}
		)
	obs.set_scene_item_transform(scene_uuid, result["sceneItemId"], {
		"positionX": logo_x + 10,
		"positionY": logo_y + 5,
		})
