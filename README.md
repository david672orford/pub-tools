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

Then open this URL in a web browser:

     http://localhost:5000

## The KH Player Module

This is the most well-developed of the modules. It helps you to load the videos
and illustrations for a congregation meeting into OBS Studio ready to play.

The KH Player module communicates with OBS over websocket. You will need to use
OBS version OBS 2.8. To pair them, open OBS and enable the websocket plugin. Note the port
and password. Then open **instance/config.py** in a text editor and add
this:

    OBS_WEBSOCKET = {
      'hostname': 'localhost',
      'port': 4455,
      'password': 'secret',
      }

Replace *secret* with the password you set for the Websocket plugin in OBS.

Now start the application web server and go to http://localhost:5000/khplayer/ in a browser.
A window will appear with tabs such as **Meetings**, **Songs**,
and **Videos** which can be used to load videos material into OBS.

## OBS Scripts

The obs-scripts directory contains scripts which can be installed in OBS studio
to automate tasks required when using it at a congregation meeting.

### khplayer.py

This script runs the Pub Tools appliation web server into OBS Studio. This means
that there is no need to start it separately.

### virtual-audio-cable.py

This script creates two virtual audio cables in the Pipewire audio server and
connect them properly to feed the output of OBS Studio and the microphone into the
speakers also selected in KH Player. The microphone and speakers are selected in
KH Player in the **Audio** tab.

### autostart-outputs.py

This script starts the virtual camera and a fullscreen output on the monitor selected in
the script configuration screen. This saves time when getting things set up before
a congregation meeting.

### auto-mute.py

This script mutes the microphone when music or videos are playing. This improves sound
quality for participant in Zoom considerably.

This script also initiates a scene switch to the first scene whenever it detects that
the music or video has finished. To get the desired effect, you should make sure that
the first scene shows the stage.

## The Teaching Toolbox Module

This subapp displays a list of the publications from the Teaching Toolbox
along with the link to it on JW.ORG. It is intended to help publishers
to send links to interested persons.

Before using this module, load the lists of publications:

    $ flask update magazines
    $ flask update books
    $ flask update videos

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

