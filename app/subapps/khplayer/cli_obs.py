"""
CLI for OBS
"""

import sys
import os
import json

from flask.cli import AppGroup
import click

from .utils.controllers import obs

cli_obs = AppGroup("obs", help="Control OBS Studio")

def print_json(data):
	"""Pretty-print a dict in JSON format"""
	json.dump(data, sys.stdout, indent=4, ensure_ascii=False)
	print()

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

@cli_obs.command("get-input-default-settings")
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
	"""Given name, get UUID"""
	print(obs.get_input_uuid(input_name))

@cli_obs.command("get-input-setting-options")
@click.argument("input_name")
@click.argument("property_name")
def cmd_obs_get_input_setting_options(input_name, property_name):
	"""Get the options for the specified setting of the specified input"""
	response = obs.request("GetInputPropertiesListPropertyItems", {
		"inputName": input_name,
		"propertyName": property_name,
		})
	print_json(response["responseData"]["propertyItems"])

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

@cli_obs.command("get-input-device-list")
@click.argument("input_name", default="Mic/Aux")
def cmd_get_input_device_list(input_name):
	"""List options for device_id setting of the named input"""
	print(f"Devices for {input_name}:")
	response = obs.request("GetInputPropertiesListPropertyItems", {
		"inputName": input_name,
		"propertyName": "device_id",
		})
	print_json(response["responseData"]["propertyItems"])

@cli_obs.command("get-input-device")
@click.argument("input_name")
def cmd_get_input_device(input_name):
	"""Get the device_id setting of the named input"""
	settings = obs.get_input_settings(name=input_name)
	print(settings.get("device_id"))

@cli_obs.command("set-input-device")
@click.argument("input_name")
@click.argument("device_id")
def cmd_set_input_device(input_name, device_id):
	"""Set the device_id setting of the named input"""
	obs.set_input_settings(name=input_name, settings={"device_id": device_id})

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

@cli_obs.command("get-output-list")
def cmd_obs_get_output_list():
	"""Get list of available outputs"""
	print_json(obs.request("GetOutputList", {})["responseData"]["outputs"])
