## The KH Player Module

This is the most well-developed of the modules. It helps you to load the videos
and illustrations for a congregation meeting into OBS Studio ready to play.

This note describes how to set up OBS to play the videos at meetings while
some participants are connected by Zoom. These instructions apply to Ubuntu
Linux 22.04.

The KH Player module communicates with OBS over websocket. You will need to use
OBS version 2.8 or later. To pair them, open OBS and enable the websocket plugin.
Note the port and password. Then open **instance/config.py** in a text editor and
add this:

    OBS_WEBSOCKET = {
      'hostname': 'localhost',
      'port': 4455,
      'password': 'secret',
      }

Replace *secret* with the password you set for the Websocket plugin in OBS.

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser:

    http://localhost:5000/toolbox/

A window will appear with tabs such as **Meetings**, **Songs**,
and **Videos** which can be used to load videos material into OBS.

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

## Initial Setup of Zoom

* Under **General** enable **Use dual monitors**.
* Under **Video** select **Original ratio** and **HD**. Turn off **Mirror my video**.
* Still under **Video** choose **See myself as the active speaker while speaking**.
* Under **Audio** set **Suppress background noise** to **Low** so that music will not be muted.

## Initial Setup of OBS

* In the settings under **General** find **Projectors** and check the boxes next to
  **Make projectors always on top** and **Limit one fullscreen projector per screen**.
* In the settings under **Audio** set the **Monitoring Device** to **Monitor of To-Zoom**.
* In the settings under **Video** set the **Base (Canvas) Resolution** and **Output (Scaled) Resolution** to 1024x720.
* Enable the OBS-Websocket plugin and copy the password into the config.py file of **Pub-Tools**.
* Under **Docks** uncheck **Audio Mixer** since we will not be using it.
* Go to **Tools**, **Scripts** and add the following scripts from the **obs-scripts**
directory of this project:
  * **khplayer-startup.py** -- Automatically start the virtual camera and a fullscreen output on the monitor you select,  switch to your initial scene, and mute audio.
  * **khplayer-server.py** -- Run the Pub-Tools web server inside of OBS so we will not need
  * **khplayer-cable.py** -- Creates a To-Zoom/From-OBS virtual audio cable every time OBS starts
  * **khplayer-vidoes.py** 
    * Mute the system default input device (the microphone) when videos are playing. This improves sound quality for participant in Zoom considerably.
    * Switch to the scene you specify whenever a video finishes playing. Set this to the scene with the camera which shows the stage.
    * Stop the playing of videos from JW.ORG a few seconds before the end so the speaker will not have to wait for the end card to disappear.

## Starting the Meeting

* Start OBS.
* Start Zoom. Make sure a second window appears on the second monitor.
* Log in to Zoom and start the meeting.
* Click on the down arrow next to the camera button and select
**Dummy video device (0x0000)** as the camera. Turn it on. If it will
not turn on, make sure the virtual camera is started in OBS.
* Click on the down arrow next to the microphone button and select **From-OBS**
as the audio input and unmute audio.

## Creating Meeting Scenes

* Open **http://localhost:5000/khplayer** in a web browser
* If this the first time, go to the **Audio** tab and select the desired
microphone and speakers. Press **Reconnect Audio** to connect then to Zoom and OBS.
* If this is the first time, go to the **Scenes** tab and press the **Add a Live
Scene** button. Select the desired camera and press **Add Camera Scene**. Press
the **Add Zoom Scene** and **Add Split Screen Scenes**.
* Go to the **Meetings** tab and select the meeting and week you want. A list
of videos and illustrations will load. There will be a checkbox next to each
item. Remove the checkbox for any item you do not need and press
the **Download Media and Create Scenes in OBS** button.
* For the weekend meeting, go to the **Songs** tab and load the song chosen by
the speaker.

## Loading Clips from JW Stream

* Go to the **JW Stream** tab. Click on **Configuration**. Paste one
or more sharing URLs from JW Stream into the box and press **Save**.
* A table will appear with one row for each URL you entered. Click on the
one you want.
* A list of recorded events will appear. Click on the one you want.
* A player will appear. Find the start of the clip you want. You can use
the skip buttons and the chapter buttons to help you. Hit the **Set Start**
button.
* Find the end of the clip. Press the **Sent End** button.
* Adjust the **Clip Title**, if necessary, and press **Make Clip**.

