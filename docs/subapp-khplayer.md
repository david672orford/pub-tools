## The KH Player Subapp

This is the most well-developed of the modules. It helps you to load the videos
and illustrations for a congregation meeting into OBS Studio ready to play.

This note describes how to set up OBS to play the videos at meetings while
some participants are connected by Zoom. These instructions apply to Ubuntu
Linux 22.04.

## Install OBS Studio

On Ubuntu:

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

On Microsoft Windows:

    > winget install --id=OBSProject.OBSStudio -e

The KH Player module communicates with OBS over a websocket. You will need to use
OBS version 2.8 or later. Enable the websocket plugin in **Tools** →
**Websocket Server Settings**. If KH Player cannot find your OBS configuration
to get the websocket port and password, set OBS\_WEBSOCKET in config.py
using the example in sample-config.py.

## Test Run

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser:

    http://localhost:5000/khplayer/

A window will appear with tabs such as **Meetings**, **Songs**,
and **Videos** which can be used to load videos material into OBS.

## Install Pipewire

Install the new audio subsystem called Pipewire following the instructions
in the document [Pipewire on Debian](https://pipewire-debian.github.io/pipewire-debian/).
Be sure to follow the part about installing Wireplumber. If you are running Ubuntu 24.04
or later, then Pipewire may already be installed.

## Set Up Video Loopback Device

    $ ./docs/setup-loopback.sh

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
* TODO: Setting to prevent warning about exit with virtual camera running
* Under **Tools** find the OBS-Websocket plugin and enable it
* Under **Docks** uncheck **Audio Mixer** since we will not be using it.
* Go to **Tools**, **Scripts** and add the following scripts from the **obs-scripts**
directory of this project:
  * **khplayer-server.py** -- Run the Pub-Tools web server inside of OBS so we will not need
  * **khplayer-cable.py** -- Creates a To-Zoom/From-OBS virtual audio cable every time OBS starts
  * **khplayer-automate.py** -- Simplify startup and playing of vidoes
    * At Startup:
      * Start a fullscreen output on the monitor you select
      * Start the virtual camera
      * Switch to the yeartext scene you have selected
    * Mute the microphone whenever the yeartext scene is displayed
    * When a Video is played:
      * Mute the microphone. This improves sound quality for participant in Zoom considerably.
      * Stop the playing of videos from JW.ORG a few seconds before the end so the speaker will not have to wait for the end card to disappear.
      * Return to the state scene you specify whenever a video finishes playing.
  * TODO: **khplayer-zoom-tracker.py**

## Starting the Meeting

* Start OBS.
* Start Zoom. Make sure a second window appears on the second monitor.
* Log in to Zoom and start the meeting.
* Click on the down arrow next to the camera button and select **OBS Virtual Camera**
  as the camera. Turn it on. If it will not turn on, make sure the virtual camera is started in OBS.
* Click on the down arrow next to the microphone button and select **From-OBS**
  as the audio input and unmute audio.

## Initial Setup of Stage and Zoom Scenes

* Open **http://localhost:5000/khplayer/** in a web browser
* Go to the **Audio** tab and select the desired
microphone and loudspeakers. Press **Reconnect Audio** to connect then to Zoom and OBS.
* Go to the **Scenes** tab and press the **Add a Live
Scene** button. Select the desired camera and press **Add Camera Scene**.
* Press the **Add Zoom Scene** button.
* Press the **Add Split Screen Scenes** button. (FIXME)

## Loading Videos and Images for a Meeting

![Screenshot of the Meetings tab](images/screenshot-khplayer-meetings.png)

* Go to the **Meetings** tab and select the meeting and week you want. A list
of videos and illustrations will load. There will be a checkbox next to each
item. Remove the checkbox for any item you do not need and press
the **Download Media and Create Scenes in OBS** button.
* For the weekend meeting, go to the **Songs** tab and load the song chosen by
the speaker.

## Loading Additional Songs

![Screenshot of the Songbook tab](images/screenshot-khplayer-songbook.png)

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

## Loading Speaker's Slides

KH Player can load images and videos which you have placed in a folder to which
you have pointed it. The folder can be local or on Google Drive.

Local setup:

* Place media files in the instace/slides folder
* Go into the **Slides** tab in KH Player and press the **Settings** button
* Make sure the URL is blank and press **Save**

Google Drive setup:

* Create a new folder within your Google Drive
* Share it to "anyone who has the link". Copy the link.
* Go into the **Slides** tab in KH Player and press the **Settings** button
* Paste the Google Drive link in and press **Save**

Loading slides:

* Put any of the following into the local or Google Drive folder selected above
    * Subfolders containing JPEG, PNG, or MP4 files
    * Zip files containing JPEG, PNG, or MP4 files
    * Playlists in .jwlplaylist format
    * Playlists in .JWPUB format. If the playlist includes videos, download them too and save them in the folder alongside the .JWPUB file.
* Go back to the **Slides** tab and browse to the folder you want.
* Adjust the check marks next to the slide images and press the **Load** button.

## TODO

We need to cover these additional topics.

* Loading songs
* Drag and drop into scenes
* Renaming Cameras
* Subtitles
* Virtual Camera
* Equalizer
* Renaming Microphones
* Disabling Distracting Devices
