# JW-Pubs

This is a Python-Flask app for downloading and displaying publications from
JW.ORG. It is divided into a number of modules which can be enabled and
disabled individually in the config file.

## Install

    $ sudo apt-get install python3-pip
    $ pip3 install -r requirements.txt
    $ mkdir instance instance/cache
    $ touch instance/config.py

## Run

    $ ./start.py

Then open http://localhost:5000 in a web browser.

## JW-Meeting and OBS to Zoom

This app helps you to load the vidoes and illustrations for a meeting into OBS
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

    $ ./jw-pubs khplayer

A window will appear with three tabs labeledr **Meetings**, **Songs**,
**Videos**, and **OBS**.. Clicking on a meeting, song, or video to
download it and add it to the scene list in OBS.

## Teaching Toolbox

This subapp displays a list of the publications from the Teaching Toolbox
along with the link to it on JW.ORG. It is intended to help publishers
to send links to interested persons.

To run it, first load the lists of publications:

    $ flask update magazines
    $ flask update books
    $ flask update videos

Then run this command command:

    $ ./jw-pubs toolbox

## ePub Viewer

This is an experimental framework for downloading and viewing Epub files
from JW.ORG in a web browser.

To see what it can do so far, first run one or more of the following commands
to download the lists of available publications:

    $ flask update magazines
    $ flask update books

Then run this command:

    $ ./jw-pubs epubs

If you click on a link, you will get 404. To download the ePub file, note the last
element in the URL. This is the publication or issue code. Then run one of the
following commands:

    $ flask epub download-book **publications code**

or

    $ flask epub download-issue **issue code**

If the ePub viewer ever moves beyond the experimental state, we will implement
downloading of ePub files from the web interface.

