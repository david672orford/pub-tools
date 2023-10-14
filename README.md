# Pub-Tools

Pub-Tools is a Python-Flask app for downloading and displaying publications from
JW.ORG. It is divided into a number of modules which can be enabled and
disabled individually in the config file.

## Install on Ubuntu and other Debian-Family Linuxes

    $ sudo apt-get install git python3-pip ffmpeg python3-ewmh
    $ git clone https://github.com/david672orford/pub-tools.git
    $ cd pub-tools
    $ pip3 install -r requirements.txt

## Run

Start the application web server:

    $ ./start.py

and then open http://localhost:5000 in a web browser.

Or run this script to start the web server and a web browser widget:

    $ ./pub-tools

## The KH Player Module

This app helps you to load the videos and illustrations for a meeting into OBS
Studio ready to play.

First open OBS 2.8 or later and enable the websocket plugin. Note the port
and password. Then open **instance/config.py** in a text editor and add
this:

    OBS_WEBSOCKET = {
      'hostname': 'localhost',
      'port': 4455,
      'password': 'secret',
      }

Replace *secret* with the password you set for the Websocket plugin in OBS.

Then run this command:

    $ ./pub-tools khplayer

A window will appear with tabs such as **Meetings**, **Songs**,
**Videos**, **JW Stream** which can be used to load videos and illustrations.

## OBS Scripts

The obs-scripts directory contains scripts which you can load into OBS Studio.

### khplayer.py

Run the Pub Tools web app inside of OBS Studio.

### virtual-audio-cable.py

Call into KH Player to create two virtual audio cables in the Pipewire
audio server and connect them properly to feed the output of OBS Studio 
and the microphone selected in KH Player into Zoom and into the
speakers also selected in KH Player.

### autostart-outputs.py

Start the virtual camera and a fullscreen output on the monitor selected in
the script configuration screen.

### auto-mute.py

Mute the system default input device (which should be the microphone) whenever
a video is playing in OBS Studio. Return the the first scene (which should
show the camera) whenever a video stops playing.

## The Teaching Toolbox Module

This subapp displays a list of the publications from the Teaching Toolbox
along with the link to it on JW.ORG. It is intended to help publishers
to send links to interested persons.

To run it, first load the lists of publications:

    $ flask update magazines
    $ flask update books
    $ flask update videos

Then run this command:

    $ ./pub-tools toolbox

## The Epub Viewer Module

This is an experimental framework for downloading and viewing Epub files
from JW.ORG in a web browser.

To see what it can do so far, first run one or more of the following commands
to download the lists of available publications:

    $ flask update magazines
    $ flask update books

Then run this command to see the list of publications:

    $ ./pub-tools epub-viewer

If you click on a link, you will get 404. To download the ePub file, note the
publication code which is the last component of the URL path. Then run this
command:

    $ flask epub download **pub code**

If the ePub Viewer module ever moves beyond the experimental state, we will
add a button or other control for downloading the ePub files directly from
the web interface.

## TODO

* Fix bin/virtual-audio-cable

