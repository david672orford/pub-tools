#! /bin/bash

# Load video loopback device at boot, make it /dev/video10 with
# the name "OBS Virtual Camera".
echo v4l2loopback \
	| sudo tee /etc/modules-load.d/v4l2loopback.conf
echo 'options v4l2loopback video\_nr=10 card_label="OBS Virtual Camera"' \
	| sudo tee /etc/modprobe.d/v4l2loopback.conf

# Start it now
sudo modprobe v4l2loopback

