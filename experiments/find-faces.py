#! /usr/bin/python3

# See:
# https://pypi.org/project/face-recognition/

import face_recognition
from PIL import Image, ImageDraw

while True:
	print("Starting.")
	image = face_recognition.load_image_file("face.jpg")
	face_locations = face_recognition.face_locations(image)
	print("face_locations:", face_locations)

image = Image.open("face.jpg")
draw = ImageDraw.Draw(image)
for top, right, bottom, left in face_locations:
	draw.rectangle(((left, top), (right, bottom)), outline="red")
image.show()
