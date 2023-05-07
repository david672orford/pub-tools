# Setting up OBS to Broadcast through Zoom

This note describes how to set up OBS to play the videos at meetings while
some participants are connected by Zoom.

These instructions apply to Ubuntu Linux 22.04.

## Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install the Video For Linux Loopback Device

    $ sudo modprobe v4l2loopback
	$ sudo sh -c 'echo v4l2loopback >>/etc/modules'

## Install Pipewire

Install the new audio subsystem called Pipewire following the instructions
in the document [Pipewire on Debian](https://pipewire-debian.github.io/pipewire-debian/).
Be sure to follow the part about installing Wireplumber.

## Create the Virtual Audio Cable

Run this script which we supply:

    $ ./bin/virtual-audio-cable create connect-peripherals

Until we figure out how to add it to the configuration you will have to run this
ever time you log in.

## Initial Setup of Zoom

* Under **General** enable **Use dual monitors**.
* Under **Video** select **Original ratio** and **HD**. Turn off **Mirror my video**.
* Still under **Video** choose **See myself as the active speaker while speaking**.
* Under **Audio** set **Suppress background noise** to **Medium** so that music will not be muted.

## Initial Setup of OBS

* In the settings under **General** find **Projectors** and check the boxes next to
  **Make projectors always on top** and **Limit one fullscreen projector per screen**.
* In the settings under **Audio** set the **Monitoring Device** to **Monitor of To-Zoom**.
* In the settings under **Video** set the **Base (Canvas) Resolution** and **Output (Scaled) Resolution** to 1024x720.
* Enable the OBS-Websocket plugin and copy the password into the config.py file of **Pub-Tools**.
* Under **Docks** uncheck **Audio Mixer** since we will not be using it.

## Starting the Meeting

* Start OBS. Start the virtual camera.
* In OBS create a scene and add a V4l2 input. Select the camera (the real one).
* Create another scene with a window capture. Capture the second Zoom window.
* Start Zoom. Make sure a second window appears on the second monitor.
* Log in and start the meeting.
* Select **From-OBS** as the audio input.
* Unmute audio.
* Select **Dummy video device (0x0000)** as the camera.
* Turn the camera on. If it will not turn on, go back to OBS and make sure you have
  started it there.
* Go to OBS, right click on the video preview (the one on the right if you are in
  Studio Mode) and select under **Fullscreen Project** pick the second one. Fullscreen
  output from OBS will cover the second Zoom window on the second monitor.
* Start **Pub-Tools** and load the meeting vidoes and illustrations.

