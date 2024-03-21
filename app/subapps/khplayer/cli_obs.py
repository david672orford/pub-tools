from flask.cli import AppGroup
import click
import sys, os, json

from .utils.controllers import obs

cli_obs = AppGroup("obs", help="Control OBS Studio")

def print_json(data):
	json.dump(data, sys.stdout, indent=4, ensure_ascii=False)
	print()

# Pretty print the JSON file which contains the scene list.
# This is useful for getting the parameters to construct scenes programatically.
@cli_obs.command("dump-scenes", help="Pretty-print KH Player scene collection")
def cmd_obs_dump_scenes():
	with open("%s/.config/obs-studio/basic/scenes/KH_Player.json" % os.environ["HOME"]) as f:
		data = json.load(f)
	print_json(data)

@cli_obs.command("get-version", help="Show OBS version and features")
def cmd_obs_get_version():
	print_json(obs.get_version())

@cli_obs.command("get-scene-list", help="List scenes by name")
def cmd_obs_get_scene_list():
	print_json(obs.get_scene_list())

@cli_obs.command("get-scene-uuid", help="Given name, get scene UUID")
@click.argument("scene_name")
def cmd_get_scene_uuid(scene_name):
	print(obs.get_scene_uuid(scene_name))

@cli_obs.command("get-scene-item-list", help="Show the items in the specified scene")
@click.argument("scene_uuid")
def cmd_obs_get_scene_item_list(scene_uuid):
	for item in obs.get_scene_item_list(scene_uuid):
		print_json(item)

@cli_obs.command("get-scene-item-transform", help="Show the coordinate transform of scene item")
@click.argument("scene_uuid")
@click.argument("scene_item_id", type=click.IntRange(min=1), default=1)
def cmd_obs_get_scene_item_transform(scene_uuid, scene_item_id):
	print_json(obs.get_scene_item_transform(scene_uuid, scene_item_id))

@cli_obs.command("get-scene-item-private-settings", help="Show the private settings of scene item")
@click.argument("scene_uuid")
@click.argument("scene_item_id", type=click.IntRange(min=1), default=1)
def cmd_obs_get_scene_item_private_settings(scene_uuid, scene_item_id):
	print_json(obs.get_scene_item_private_settings(scene_uuid, scene_item_id))

@cli_obs.command("get-input-list", help="List inputs by name")
def cmd_obs_get_input_list():
	print_json(obs.get_input_list())

@cli_obs.command("get-input-uuid", help="Given name, get UUID")
@click.argument("input_name")
def cmd_obs_get_input_uuid(input_name):
	print(obs.get_input_uuid(input_name))

@cli_obs.command("get-input-settings", help="Show settings of specified input")
@click.argument("input_uuid")
def cmd_obs_get_input_settings(input_uuid):
	print_json(obs.get_input_settings(input_uuid))

@cli_obs.command("set-input-settings", help="Change settings of specified input")
@click.argument("input_uuid")
@click.argument("settings")
def cmd_obs_set_input_settings(input_uuid, settings):
	settings = json.loads(settings)
	obs.set_input_settings(input_uuid, settings, overlay)

@cli_obs.command("get-source-filter-list", help="Show filters in named source")
@click.argument("source_name")
def cmd_obs_get_source_filter_list(source_name):
	print_json(obs.request("GetSourceFilterList", {"sourceName": source_name}))

@cli_obs.command("save-source-screenshot", help="Take a screenshot of named source")
@click.argument("source_name")
def cmd_obs_save_source_screenshot(source_name):
	response = obs.request("SaveSourceScreenshot", {
		"sourceName": source_name,
		"imageFormat": "jpeg",
		"imageFilePath": os.path.abspath(source_name + ".jpg"),
		})
	print_json(response)

@cli_obs.command("get-output-list", help="Get list of available outputs")
def cmd_obs_get_output_list():
	print_json(obs.request("GetOutputList"))

@cli_obs.command("get-hotkey-list", help="List defined hotkeys")
def cmd_obs_get_hotkey_list():
	response = obs.request("GetHotkeyList", {})
	print_json(response)

