"""
CLI for OBS
"""

import sys
import os
import json

from flask.cli import AppGroup
import click
from rich.console import Console
from rich.table import Table

from .utils.controllers import obs

cli_obs = AppGroup("obs", help="Control OBS Studio")

def print_json(data):
	"""Pretty-print a dict in JSON format"""
	json.dump(data, sys.stdout, indent=4, ensure_ascii=False)
	print()

#=============================================================================
# Perform the initial setup of OBS up for use with KH Player
#=============================================================================

@cli_obs.command("configure")
def cmd_obs_configure():
	obs.create_profile("KH Player", reuse=True)
	obs.create_scene_collection("KH Player", reuse=True)
	obs.set_video_settings({
		"baseHeight": 720,
		"baseWidth": 1280,
		"fpsDenominator": 1,
		"fpsNumerator": 30,
		"outputHeight": 720,
		"outputWidth": 1280
		})

#=============================================================================
# Misc info
#=============================================================================

@cli_obs.command("get-version", help="Show OBS version and features")
def cmd_obs_get_version():
	print_json(obs.get_version())

@cli_obs.command("get-hotkey-list", help="List defined hotkeys")
def cmd_obs_get_hotkey_list():
	response = obs.request("GetHotkeyList", {})
	print_json(response)

#=============================================================================
# Scenes
#=============================================================================

# Pretty print the JSON file which contains the scene collection
# This is useful for getting the parameters to construct scenes programatically.
@cli_obs.command("dump-scenes")
def cmd_obs_dump_scenes():
	"""Pretty-print scene collection KH Player"""
	filename = f"{os.environ['HOME']}/.config/obs-studio/basic/scenes/KH_Player.json"
	with open(filename, encoding="utf8") as fh:
		data = json.load(fh)
	print_json(data)

@cli_obs.command("get-scene-list")
def cmd_obs_get_scene_list():
	"""List scenes by name"""
	print_json(obs.get_scene_list())

@cli_obs.command("get-group-list")
def cmd_obs_get_group_list():
	"""List groups by name"""
	print_json(obs.get_group_list())

@cli_obs.command("get-scene-uuid")
@click.argument("scene_name")
def cmd_get_scene_uuid(scene_name):
	"""Given name, get scene UUID"""
	print(obs.get_scene_uuid(scene_name))

#=============================================================================
# Scene Items
#=============================================================================

@cli_obs.command("get-scene-item-list")
@click.argument("scene_uuid")
def cmd_obs_get_scene_item_list(scene_uuid):
	"""Show the items in the specified scene"""
	for item in obs.get_scene_item_list(scene_uuid):
		print_json(item)

@cli_obs.command("get-scene-item-transform")
@click.argument("scene_uuid")
@click.argument("scene_item_id", type=click.IntRange(min=1), default=1)
def cmd_obs_get_scene_item_transform(scene_uuid, scene_item_id):
	"""Show the coordinate transform of scene item"""
	print_json(obs.get_scene_item_transform(scene_uuid, scene_item_id))

@cli_obs.command("get-scene-item-settings")
@click.argument("scene_uuid")
@click.argument("scene_item_id", type=click.IntRange(min=1), default=1)
def cmd_obs_get_scene_item_private_settings(scene_uuid, scene_item_id):
	"""Show the private settings of scene item"""
	print_json(obs.get_scene_item_private_settings(scene_uuid, scene_item_id))

#=============================================================================
# Inputs
#=============================================================================

@cli_obs.command("get-input-kind-list")
def cmd_obs_get_input_kind_list():
	"""Get list of available input types"""
	response = obs.request("GetInputKindList", {})
	print_json(response["responseData"])

@cli_obs.command("get-input-list")
def cmd_obs_get_input_list():
	"""List configured inputs by name"""
	print_json(obs.get_input_list())

@cli_obs.command("get-special-inputs")
def cmd_get_special_inputs():
	"""List the scene-independent audio inputs"""
	response = obs.request("GetSpecialInputs", {})
	print_json(response["responseData"])

@cli_obs.command("create-input")
@click.argument("scene_name")
@click.argument("input_kind")
@click.argument("input_name")
def cmd_obs_create_input(scene_name, input_kind, input_name):
	response = obs.request("CreateInput", {
		"sceneName": scene_name,
		"inputKind": input_kind,
		"inputName": input_name,
		})
	print_json(response["responseData"])

@cli_obs.command("get-input-defaults")
@click.argument("input_kind")
def cmd_obs_get_input_default_settings(input_kind):
	"""Get the defaults for an input kind"""
	response = obs.request("GetInputDefaultSettings", {
		"inputKind": input_kind,
		})
	print_json(response["responseData"])

@cli_obs.command("get-input-uuid")
@click.argument("input_name")
def cmd_obs_get_input_uuid(input_name):
	"""Given name, get UUID of input"""
	print(obs.get_input_uuid(input_name))

@cli_obs.command("get-input-setting-options")
@click.argument("input_name")
@click.argument("property_name")
def cmd_obs_get_input_setting_options(input_name, property_name):
	"""Get the options for the specified setting of the specified input"""
	print_json(obs.get_input_setting_options(input_name, property_name))

@cli_obs.command("get-input-settings")
@click.argument("input_name")
def cmd_obs_get_input_settings(input_name):
	"""Show all settings of specified input"""
	print_json(obs.get_input_settings(name=input_name))

@cli_obs.command("set-input-settings")
@click.argument("input_name")
@click.argument("settings")
def cmd_obs_update_input_settings(input_name, settings):
	"""Merge JSON into settings of specified input"""
	settings = json.loads(settings)
	obs.set_input_settings(name=input_name, settings=settings)

@cli_obs.command("select-input-dev")
@click.argument("input_name", nargs=-1)
def cmd_obs_select_input_dev(input_name):
	"""Allow the user to pick an input's device from available options"""
	if len(input_name) > 0:
		input_name = input_name[0]
	else:
		options = obs.get_input_list()
		table = Table(show_header=True, title="Available Inputs", show_lines=False)
		table.add_column("Enter")
		table.add_column("Input Kind")
		table.add_column("Input Name")
		i = 1
		for option in options:
			table.add_row(str(i), option["inputKind"], option["inputName"])
			i += 1
		Console().print(table)
		if (selection := get_choice(options)) is not None:
			input_name = selection["inputName"]
		else:
			print("Not a valid choice")
			return

	settings = obs.get_input_settings(name=input_name)
	match settings["inputKind"]:
		case "xcomposite_input":
			option_name = "capture_window"
		case "pulse_input_capture":
			option_name = "device_id"
		case _:
			print("Inputs if {kind} not supported".format(kind=settings["inputKind"]))
			return

	options = obs.get_input_setting_options(input_name, option_name)
	current_value = settings["inputSettings"][option_name]
	table = Table(show_header=True, title="Available Devices", show_lines=False)
	table.add_column("Enter")
	table.add_column("Current")
	table.add_column("Device Name")
	i = 1
	for option in options:
		table.add_row(
			str(i),
			"*" if option["itemValue"] == current_value else "",
			option["itemName"],
			)
		i += 1
		Console().print(table)
	if (selection := get_choice(options)) is not None:
		obs.set_input_settings(name=input_name, settings={option_name: selection["itemValue"]})
	else:
		print("Not a valid option")

def get_choice(options):
	response = input("> ")
	try:
		response = int(response)
	except ValueError:
		return None
	response = response - 1
	if 0 <= response < len(options):
		return options[response]
	return None

#=============================================================================
# Sources
#=============================================================================

@cli_obs.command("get-source-filter-list")
@click.argument("source_name")
def cmd_obs_get_source_filter_list(source_name):
	"""Show filters in named source"""
	print_json(obs.request("GetSourceFilterList", {"sourceName": source_name}))

@cli_obs.command("save-source-screenshot")
@click.argument("source_name")
def cmd_obs_save_source_screenshot(source_name):
	"""Take a screenshot of named source"""
	response = obs.request("SaveSourceScreenshot", {
		"sourceName": source_name,
		"imageFormat": "jpeg",
		"imageFilePath": os.path.abspath(source_name + ".jpg"),
		})
	print_json(response)

#=============================================================================
# Outputs
#=============================================================================

@cli_obs.command("get-video-settings")
def cmd_obs_get_video_settings():
	"""Get the output video resolution and other settings"""
	print_json(obs.get_video_settings())

@cli_obs.command("get-output-list")
def cmd_obs_get_output_list():
	"""Get list of available outputs"""
	print_json(obs.request("GetOutputList", {})["responseData"]["outputs"])
