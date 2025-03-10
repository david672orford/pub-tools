"""
CLI for OBS
"""

import sys
import os
import json
from time import sleep
import uuid
import subprocess
import logging

from flask import current_app
from flask.cli import AppGroup
import click
from rich.console import Console
from rich.table import Table

from .utils.controllers import obs, ObsError
from .utils.obs_config import ObsConfig
from .utils.yeartext import create_yeartext_scene
from ...utils.babel import gettext as _

cli_obs = AppGroup("obs", help="Control OBS Studio")

def print_json(data):
	"""Pretty-print a dict in JSON format"""
	json.dump(data, sys.stdout, indent=4, ensure_ascii=False)
	print()

#=============================================================================
# Perform the initial setup of OBS up for use with KH Player
#=============================================================================

@cli_obs.command("setup")
def cmd_obs_setup():
	"""Set up OBS to work well with KH Player"""
	logging.basicConfig(level=logging.DEBUG)

	obs_config = ObsConfig()

	websocket_config = obs_config.websocket_config()
	if websocket_config is None:
		print("No OBS configuration found")
		return

	print("Enabling OBS-Websocket...")
	if not websocket_config.get("obs_websocket_enabled", False):
		obs_config.enable_websocket()

	print("Starting OBS...")
	obs_handle = subprocess.Popen(["obs"])

	while True:
		try:
			obs.get_version()
			break
		except ObsError as e:
			print("Waiting for OBS to start...")
			sleep(2)

	print("Stopping virtual camera...")
	try:
		obs.set_virtual_camera_status(False)
		while True:
			if obs.get_virtual_camera_status() is False:
				break
			sleep(1)
	except ObsError as e:
		if e.code != 501:
			raise

	print("Creating scene collection...")
	obs.create_scene_collection("KH Player", reuse=True)

	print("Creating profile...")
	obs.create_profile("KH Player", reuse=True)
	obs.set_video_settings({
		"baseHeight": 720,
		"baseWidth": 1280,
		"fpsDenominator": 1,
		"fpsNumerator": 30,
		"outputHeight": 720,
		"outputWidth": 1280
		})

	try:
		from ewmh import EWMH
		wm = EWMH()
		for window in wm.getClientList():
			name = wm.getWmName(window).decode("utf-8")
			print("window:", name)
			if name.startswith("OBS"):
				print("Asking OBS to close...")
				wm.setCloseWindow(window)
				wm.display.flush()
				break
	except ModuleNotFoundError:
		print("Module ewmh not found")

	while(obs_handle.returncode is None):
		print("Now please close OBS.")
		try:
			obs_handle.wait(2)
			break
		except subprocess.TimeoutExpired:
			pass

	print("General configuration...")
	config = obs_config.get_config()
	config["General"]["ConfirmOnExit"] = "false"
	config["BasicWindow"]["SideDocks"] = "true"
	config["BasicWindow"]["ProjectorAlwaysOnTop"] = "true"
	config["BasicWindow"]["CloseExistingProjectors"] = "true"
	config.set("BasicWindow", "ExtraBrowserDocks", json.dumps([
		{
			"title": "KH Player",
			"url": "http://localhost:5000/khplayer/",
			"uuid": uuid.uuid4().hex,
		}
		]))
	config["BasicWindow"]["geometry"] = "AdnQywADAAAAAAAAAAAAJAAABSIAAANiAAAAAwAAADwAAAUfAAADXwAAAAAAAAAACZoAAAADAAAAPAAABR8AAANf"
	config["BasicWindow"]["DockState"] = "AAAA/wAAAAD9AAAAAgAAAAAAAAJHAAAC6/wCAAAAAfsAAAAsAEsASAAgAFAAbABhAHkAZQByAF8AZQB4AHQAcgBhAEIAcgBvAHcAcwBlAHIBAAAAFwAAAusAAABQAP///wAAAAMAAALSAAAA/PwBAAAABvsAAAAUAHMAYwBlAG4AZQBzAEQAbwBjAGsAAAAA7QAAAJgAAACYAP////sAAAAWAHMAbwB1AHIAYwBlAHMARABvAGMAawEAAAJLAAAAoAAAAJgA////+wAAABIAbQBpAHgAZQByAEQAbwBjAGsBAAAC7wAAAO4AAADeAP////sAAAAeAHQAcgBhAG4AcwBpAHQAaQBvAG4AcwBEAG8AYwBrAAAAAq4AAADsAAAAggD////7AAAAGABjAG8AbgB0AHIAbwBsAHMARABvAGMAawEAAAPhAAABPAAAAScA////+wAAABIAcwB0AGEAdABzAEQAbwBjAGsCAAADbwAAAk8AAAK8AAAAyAAAAtIAAAHrAAAAAQAAAAIAAAABAAAAAvwAAAAA"
	if sys.platform == "win32":
		config.set("Python", "Path64bit", os.path.join(current_app.root_path, "..", "python"))
	if not "Appearance" in config:
		config["Appearance"] = {}
	config["Appearance"]["Theme"] = "com.obsproject.Yami.Light"
	obs_config.save_config(config)

	print("Adding scripts to scene collection...")
	scenes = obs_config.get_scene_collection("KH Player")
	scripts = []
	for filename, settings in (
			("khplayer-server.py", {"enable": True}),
			("khplayer-automate.py", {}),
			("khplayer-zoom-participant.lua", {}),
			("khplayer-zoom-tracker.py", {}),
		):
		scripts.append({
			"path": os.path.join(current_app.root_path, "..", "obs-scripts", filename),
			"settings": settings,
			})
	scenes["modules"]["scripts-tool"] = scripts
	obs_config.save_scene_collection("KH Player", scenes)

	print("Done.")

#=============================================================================
# Misc info
#=============================================================================

@cli_obs.command("get-version")
def cmd_obs_get_version():
	"""Show OBS version and features"""
	print_json(obs.get_version())

@cli_obs.command("get-hotkey-list")
def cmd_obs_get_hotkey_list():
	"""List defined hotkeys"""
	response = obs.request("GetHotkeyList", {})
	print_json(response)

#=============================================================================
# Scenes
#=============================================================================

@cli_obs.command("dump-scene-collection")
def cmd_obs_dump_scene_collection():
	"""Pretty-print scene collection 'KH Player'"""
	obs_config = ObsConfig()
	scene_collection = obs_config.get_scene_collection("KH Player")
	print_json(scene_collection)

@cli_obs.command("get-scene-list")
def cmd_obs_get_scene_list():
	"""List scenes by name"""
	table = Table(show_header=True, title="Scenes", show_lines=False)
	for col in ("Idx", "Scene Name", "Scene UUID"):
		table.add_column(col)
	for scene in obs.get_scene_list()["scenes"]:
		table.add_row(str(scene["sceneIndex"]), scene["sceneName"], scene["sceneUuid"])
	Console().print(table)

@cli_obs.command("get-group-list")
def cmd_obs_get_group_list():
	"""List groups by name"""
	print_json(obs.get_group_list())

@cli_obs.command("get-scene-uuid")
@click.argument("scene_name")
def cmd_get_scene_uuid(scene_name):
	"""Given name, get scene UUID"""
	print(obs.get_scene_uuid(scene_name))

@cli_obs.command("create-scene")
@click.argument("scene_name")
def cmd_create_scene(scene_name):
	"""Create a new empty scene"""
	obs.create_scene(scene_name)

#=============================================================================
# Scene Items
#=============================================================================

@cli_obs.command("get-scene-item-list")
@click.argument("scene_name")
def cmd_obs_get_scene_item_list(scene_name):
	"""Show the items in the specified scene"""
	table = Table(show_header=True, title="Scene Items", show_lines=False)
	for col in (
			"Idx",
			"ID",
			"Is Group",
			"Input Kind",
			"Source Type",
			"Name",
			"Enabled",
			"Locked",
			"Blend Mode",
			"Source UUID",
			#"Transform",
			):
		table.add_column(col)
	for item in obs.get_scene_item_list(scene_name=scene_name):
		#print_json(item)
		table.add_row(*[str(item[name]) for name in (
			"sceneItemIndex",
			"sceneItemId",
			"isGroup",
			"inputKind",
			"sourceType",
			"sourceName",
			"sceneItemEnabled",
			"sceneItemLocked",
			"sceneItemBlendMode",
			"sourceUuid",
			#"sceneItemTransform",
			)])
		Console().print(table)

@cli_obs.command("get-scene-item-transform")
@click.argument("scene_name")
@click.argument("scene_item_id", type=click.IntRange(min=1), default=1)
def cmd_obs_get_scene_item_transform(scene_name, scene_item_id):
	"""Show the coordinate transform of scene item"""
	print_json(obs.get_scene_item_transform(scene_name=scene_name, scene_item_id=scene_item_id))

@cli_obs.command("get-scene-item-settings")
@click.argument("scene_name")
@click.argument("scene_item_id", type=click.IntRange(min=1), default=1)
def cmd_obs_get_scene_item_private_settings(scene_name, scene_item_id):
	"""Show the private settings of scene item"""
	print_json(obs.get_scene_item_private_settings(scene_name=scene_name, scene_item_id=scene_item_id))

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
@click.argument("input_settings")
def cmd_obs_create_input(scene_name, input_kind, input_name, input_settings):
	"""Create a new input in a specified scene"""
	response = obs.request("CreateInput", {
		"sceneName": scene_name,
		"inputKind": input_kind,
		"inputName": input_name,
		"inputSettings": json.loads(input_settings),
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
		for col in ("Enter", "Input Kind", "Input Name"):
			table.add_column(col)
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
		case "v4l2_input":
			option_name = "device_id"
		case _:
			print("Inputs if {kind} not supported".format(kind=settings["inputKind"]))
			return

	options = obs.get_input_setting_options(input_name, option_name)
	current_value = settings["inputSettings"][option_name]
	table = Table(show_header=True, title="Available Devices", show_lines=False)
	for col in ("Enter", "Current", "Device Name"):
		table.add_column(col)
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
	"""Get the canvas and output video resolutions and framerate"""
	print_json(obs.get_video_settings())

@cli_obs.command("set-video-settings")
@click.argument("settings")
def cmd_obs_set_video_settings(settings):
	"""Set the canvas and output video resolutions and framerate"""
	settings = json.loads(settings)
	obs.set_video_settings(settings)

@cli_obs.command("get-output-list")
def cmd_obs_get_output_list():
	"""Get list of available outputs"""
	print_json(obs.request("GetOutputList", {})["responseData"]["outputs"])

@cli_obs.command("stop-vcam")
def cmd_obs_stop_vcam():
	"""Stop the virtual camera"""
	obs.set_virtual_camera_status(False)

@cli_obs.command("start-vcam")
def cmd_obs_stop_vcam():
	"""Start the virtual camera"""
	obs.set_virtual_camera_status(True)

#=============================================================================
# Create a scene with the yeartext (provided on the command line)
#=============================================================================

@cli_obs.command("create-yeartext")
def cmd_create_yeartext():
	"""Get the current yeartext and put it in a scene"""
	create_yeartext_scene()
