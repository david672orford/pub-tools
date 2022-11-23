# OBS and Zoom

This note describes how to set up OBS to play the videos at meetings while
some participants are connected by Zoom.

## Install OBS Studio on Ubuntu Linux

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install the Video For Linux Loopback Device

    $ sudo modprobe v4l2loopback
	$ sudo sh -c 'echo v4l2loopback >>/etc/modules'

## Create the Virtual Audio Cable

We are still working on this.

## Initial Setup of Zoom

* Under **General** enable **Use dual monitors**.
* Under **Video** select **Original ratio** and **HD**. Turn off **Mirror my video**.

## Initial Setup of OBS

* In the settings under **Video** set the **Base (Canvas) Resulution** and **Output (Scaled) Resolution** to 1024x720.
* In the settings under **Audio** set the **Monitoring Device** to **Monitor of To-Zoom**.
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
* Start Pub-Tools and load the meeting vidoes and illustrations.

