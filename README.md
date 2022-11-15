# Pub-Tools

Pub-Tools Python-Flask app for downloading and displaying publications from
JW.ORG. It is divided into a number of modules which can be enabled and
disabled individually in the config file.

## Install on Ubuntu and other Debian-Family Linuxes

    $ sudo apt-get install python3-pip ffmpeg
    $ pip3 install -r requirements.txt
    $ touch instance/config.py

## Run

    $ ./pub-tools

Or:

    $ ./start.py

and then open http://localhost:5000 in a web browser.

## KH-Meeting Module

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

Change the *secret* to the actual password.

Now download the lists of upcoming meetings and videos from JW.ORG:

    $ flask update meetings
    $ flask update videos

Finally, run this command:

    $ ./pub-tools khplayer

A window will appear with three tabs labeledr **Meetings**, **Songs**,
**Videos**, and **OBS**.. Clicking on a meeting, song, or video to
download it and add it to the scene list in OBS.

## Toolbox Module

This subapp displays a list of the publications from the Teaching Toolbox
along with the link to it on JW.ORG. It is intended to help publishers
to send links to interested persons.

To run it, first load the lists of publications:

    $ flask update magazines
    $ flask update books
    $ flask update videos

Then run this command command:

    $ ./pub-tools toolbox

## Epub Viewer Module

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

