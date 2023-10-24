from flask.cli import AppGroup
import click
import json
import sys, os

from .utils import obs

cli_obs = AppGroup("obs", help="Control OBS Studio")

# Pretty print the JSON file which contains the scene list.
# This is useful for getting the parameters to construct scenes programatically.
@cli_obs.command("dump-scenes", help="Pretty-print KH Player scene collection")
def cmd_obs_dump_scenes():
	with open("%s/.config/obs-studio/basic/scenes/KH_Player.json" % os.environ["HOME"]) as f:
		data = json.load(f)
		json.dump(data, sys.stdout, indent=4)

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
	response = obs.request("GetSceneItemList", {
		"sceneName": scene_name,
		})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-input-list", help="List inputs by name")
def cmd_obs_get_input_list():
	response = obs.request("GetInputList", {})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-input-settings", help="Show settings of specified input")
@click.argument("input_name")
def cmd_obs_get_input_settings(input_name):
	response = obs.request("GetInputSettings", {"inputName": input_name})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-source-filter-list", help="Show filters in named source")
@click.argument("source_name")
def cmd_obs_get_source_filter_list(source_name):
	response = obs.request("GetSourceFilterList", {"sourceName": source_name})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-source-screenshot", help="Take a screenshot of named source")
@click.argument("source_name")
def cmd_obs_get_source_screenshot(source_name):
	response = obs.request("GetSourceScreenshot", {
		"sourceName": source_name,
		"imageFormat": "jpeg",
		"imageWidth": 64,
		})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-output-list", help="Get list of available outputs")
def cmd_obs_get_output_list():
	response = obs.request("GetOutputList", {})
	print(json.dumps(response, indent=2, ensure_ascii=False))

