from flask.cli import AppGroup
import click
import json
import sys, os

from .utils.controllers import obs

cli_obs = AppGroup("obs", help="Control OBS Studio")

# Pretty print the JSON file which contains the scene list.
# This is useful for getting the parameters to construct scenes programatically.
@cli_obs.command("dump-scenes", help="Pretty-print KH Player scene collection")
def cmd_obs_dump_scenes():
	with open("%s/.config/obs-studio/basic/scenes/KH_Player.json" % os.environ["HOME"]) as f:
		data = json.load(f)
		json.dump(data, sys.stdout, indent=4, ensure_ascii=False)

@cli_obs.command("get-version", help="Show OBS version and features")
def cmd_obs_get_version():
	response = obs.request("GetVersion", {})
	print(json.dumps(response["responseData"], indent=2, ensure_ascii=False))

@cli_obs.command("get-scene-list", help="List scenes by name")
def cmd_obs_get_scene_list():
	for scene in obs.get_scene_list():
		print(json.dumps(scene, indent=2, ensure_ascii=False))

@cli_obs.command("get-scene-item-list", help="Show the items in a named scene")
@click.argument("scene_name")
def cmd_obs_get_scene_item_list(scene_name):
	for item in obs.get_scene_item_list(scene_name):
		print(json.dumps(item, indent=2, ensure_ascii=False))

@cli_obs.command("get-input-list", help="List inputs by name")
def cmd_obs_get_input_list():
	response = obs.request("GetInputList", {})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-input-settings", help="Show settings of specified input")
@click.argument("input_name")
def cmd_obs_get_input_settings(input_name):
	response = obs.request("GetInputSettings", {"inputName": input_name})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("set-input-settings", help="Change settings of specified input")
@click.argument("input_name")
@click.argument("settings")
def cmd_obs_set_input_settings(input_name, settings):
	settings = json.loads(settings)
	response = obs.request("SetInputSettings", {
		"inputName": input_name,
		"inputSettings": settings,
		"overlay": True,
		})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-source-filter-list", help="Show filters in named source")
@click.argument("source_name")
def cmd_obs_get_source_filter_list(source_name):
	response = obs.request("GetSourceFilterList", {"sourceName": source_name})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("save-source-screenshot", help="Take a screenshot of named source")
@click.argument("source_name")
def cmd_obs_save_source_screenshot(source_name):
	response = obs.request("SaveSourceScreenshot", {
		"sourceName": source_name,
		"imageFormat": "jpeg",
		"imageFilePath": os.path.abspath(source_name + ".jpg"),
		})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-output-list", help="Get list of available outputs")
def cmd_obs_get_output_list():
	response = obs.request("GetOutputList", {})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("face-zoom")
@click.argument("scene1_name")
@click.argument("scene2_name")
def cmd_face_zoom(scene1_name, scene2_name):
	print("Importing face_recognition...")
	import face_recognition

	scene_item = obs.get_scene_item_list(scene2_name)[0]
	scene_item_id = scene_item["sceneItemId"]
	xform = scene_item["sceneItemTransform"]

	while True:
		print("Getting screenshot...")
		response = obs.request("SaveSourceScreenshot", {
			"sourceName": scene1_name,
			"imageFormat": "jpeg",
			"imageFilePath": "/tmp/face.jpg",
			})
		#print(json.dumps(response, indent=2, ensure_ascii=False))

		image = face_recognition.load_image_file("/tmp/face.jpg")
		face_locations = face_recognition.face_locations(image)
		print("face_locations:", face_locations)

		if len(face_locations) > 0:
			top, right, bottom, left = face_locations[0]
			face_height = (bottom - top)
			print("face_height:", face_height)

			source_width = xform["sourceWidth"]
			source_height = xform["sourceHeight"]

			scale = source_height / face_height
			scaled_width = source_width * scale
			scaled_height = source_height * scale
			print(f"Scaled {source_width}x{source_height} {scale}x to {scaled_width}x{scaled_height}")

			y_center = (left + right) / 2


			new_xform = {
				"width": scaled_width,
				"height": scaled_height,
				"scaleX": scale,
				"scaleY": scale,
				"positionX": top * scale * -1,
				"positionY": (scaled_width - source_width) / -2,
				}
			print("new_xform:", new_xform)
			obs.request('SetSceneItemTransform', 
				{
				'sceneName': scene2_name,
				'sceneItemId': scene_item_id,
				'sceneItemTransform': new_xform,
	 			})
		break


