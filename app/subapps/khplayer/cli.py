from flask.cli import AppGroup
import click
import json

from ... import app
from .utils import obs

cli_obs = AppGroup("obs", help="Control OBS")
app.cli.add_command(cli_obs)

@cli_obs.command("get-version")
def cmd_obs_get_version():
	response = obs.request("GetVersion", {})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-scene-list")
def cmd_obs_get_scene_list():
	for scene in obs.get_scene_list():
		print(json.dumps(scene, indent=2, ensure_ascii=False))

@cli_obs.command("get-scene-item-list")
@click.argument("scene_name")
def cmd_obs_get_scene_item_list(scene_name):
	response = obs.request("GetSceneItemList", {
		"sceneName": scene_name,
		})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-input-list")
def cmd_obs_get_input_list():
	response = obs.request("GetInputList", {})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-input-settings")
@click.argument("input_name")
def cmd_obs_get_input_settings(input_name):
	response = obs.request("GetInputSettings", {"inputName": input_name})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-source-filter-list")
@click.argument("source_name")
def cmd_obs_get_source_filter_list(source_name):
	response = obs.request("GetSourceFilterList", {"sourceName": source_name})
	print(json.dumps(response, indent=2, ensure_ascii=False))

@cli_obs.command("get-source-screenshot")
@click.argument("source_name")
def cmd_obs_get_source_screenshot(source_name):
	response = obs.request("GetSourceScreenshot", {
		"sourceName": source_name,
		"imageFormat": "jpeg",
		"imageWidth": 64,
		})
	print(json.dumps(response, indent=2, ensure_ascii=False))

