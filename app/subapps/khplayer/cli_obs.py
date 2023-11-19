from flask.cli import AppGroup
import click
import sys, os, json
from time import sleep

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
	scene_item = obs.get_scene_item_list(scene2_name)[0]
	scene_item_id = scene_item["sceneItemId"]

	transform = scene_item["sceneItemTransform"]
	print("Existing transform:", json.dumps(transform, indent=2, ensure_ascii=False))
	image = FaceImage(transform["sourceWidth"], transform["sourceHeight"])

	slider = Slider(image)

	print("Initializing face detector...")
	#face_detector = FaceDetector1()
	face_detector = FaceDetector2()

	while True:
		print("Getting screenshot...")
		tempfile = "/tmp/face.jpg"
		response = obs.request("SaveSourceScreenshot", {
			"sourceName": scene1_name,
			"imageFormat": "jpeg",
			"imageFilePath": tempfile,
			})
		#print(json.dumps(response, indent=2, ensure_ascii=False))

		print("Looking for face...")
		faces = face_detector.detect(tempfile)
		print(f"faces: {faces}")

		if len(faces) > 0:
			face = faces[0]
			print(f"FaceBox: {face}")
			bust = BustBox(face, image)
			print(f"BustBox: {bust}")
			crop = CropBox(bust, image)
			print(f"CropBox: {crop}")

			requests = []
			for pos in slider.translate(crop.top, crop.bottom, crop.left, crop.right):
				new_xform = {
					"boundsHeight": image.height,
					"boundsWidth": image.width,
					"boundsType": "OBS_BOUNDS_STRETCH",
					"cropTop": pos.top,
					"cropBottom": (image.height - pos.bottom),
					"cropLeft": pos.left,
					"cropRight": (image.width - pos.right),
					}
				#print("new_xform:", json.dumps(new_xform, indent=4))
				requests.append({
					"requestType": "SetSceneItemTransform", 
					"requestData": {
						'sceneName': scene2_name,
						'sceneItemId': scene_item_id,
						'sceneItemTransform': new_xform,
			 			}
					})
				requests.append({
					"requestType": "Sleep",
					"requestData": {
						"sleepFrames": 1,
						}
					})

			if len(requests) > 0:
				response = obs.request_batch(requests, execution_type=1)
				#print(response)

		print("Sleeping...")
		#sleep(1)
		#break

# Dimensions of the video frame
class FaceImage:
	def __init__(self, width, height):
		self.width = width
		self.height = height

# Bounding box of detected face
class FaceBox:
	def __init__(self, order, face):
		parent = None
		i = 0
		for name in order:
			setattr(self, name, face[i])
			i += 1
	@property
	def height(self):
		return self.bottom - self.top
	@property
	def width(self):
		return self.right - self.left
	@property
	def h_center(self):
		return (self.right + self.left) / 2
	def __str__(self):
		return f"<FaceBox {self.left} to {self.right}, {self.top} to {self.bottom}>"

# Face bounding box expanded to include the presumed extent of hair, neck, and shoulders
class BustBox(FaceBox):
	def __init__(self, face, image):
		self.parent = face
		self.top = max(0, face.top - (face.height * 0.3))
		self.bottom = min(image.height, face.bottom + (face.height * 1.0))
		self.left = max(0, face.left - face.width)
		self.right = min(image.width, face.right + face.width)

# Face bounding box expanded horizontally to the aspect ration of the video frame
class CropBox(FaceBox):
	def __init__(self, bust, image):
		self.parent = bust
		self.top = bust.top
		self.bottom = bust.bottom
		half_aspect_width = bust.height * image.width / image.height / 2
		self.left = bust.h_center - half_aspect_width
		self.right = bust.h_center + half_aspect_width
		if self.left < 0:
			self.right += -self.left
			self.left = 0
		elif self.right > image.width:
			self.left -= (self.right - image.width)
			self.right = image.width

# Face detector using face_recognition
# https://github.com/ageitgey/face_recognition
class FaceDetector1:
	def __init__(self):
		from face_recognition import load_image_file, face_locations
		self.load_image_file = load_image_file
		self.face_locations = face_locations
	def detect(self, filename):
		image = self.load_image_file(filename)
		faces = []
		for face in self.face_locations(image):
			faces.append(FaceBox(("top", "right", "bottom", "left"), face))
		return faces

# Face detector using Batch-Face
# https://github.com/elliottzheng/batch-face
class FaceDetector2:
	def __init__(self):
		from cv2 import imread
		from batch_face import RetinaFace
		self.imread = imread
		self.detector = RetinaFace()
	def detect(self, filename):
		image = self.imread(filename)
		faces = []
		for face in self.detector(image, cv=True):
			box, landmarks, score = face
			faces.append(FaceBox(("left", "top", "right", "bottom"), box))
		return faces

class Slider:
	def __init__(self, image):
		self.image = image
		self.top = 0
		self.bottom = image.height
		self.left = 0
		self.right = image.width

	def translate(self, top, bottom, left, right):
		top_diff = (top - self.top)
		bottom_diff = (bottom - self.bottom)
		left_diff = (left - self.left)
		right_diff = (right - self.right)

		changes = (top_diff, bottom_diff, left_diff, right_diff)
		max_zoom_in = max(*changes)
		max_zoom_out = -min(*changes)
		print(f"max_zoom_in: {max_zoom_in}, max_zoom_out: {max_zoom_out}")
		#if max_zoom_in < 150 and max_zoom_out < 50:
		#	print("Change too small")
		#	return []
		max_diff = max(max_zoom_in, max_zoom_out)
		print(f"max_diff: {max_diff}")
		if max_diff < 1.0:
			return []

		if max_zoom_out > max_zoom_in:
			steps = max(1, int(max_diff / 10))
		else:
			steps = int(max_diff)
		print(f"steps: {steps}")
		top_step = top_diff / steps
		bottom_step = bottom_diff / steps
		left_step = left_diff / steps
		right_step = right_diff / steps

		print("Zooming and panning...")
		for i in range(steps):
			self.top += top_step
			self.bottom += bottom_step
			self.left += left_step
			self.right += right_step
			yield self

