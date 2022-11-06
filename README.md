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
Studio. To run it, first download the publication lists:

  $ flask update meetings
  $ flask update study-pubs
  $ flask update videos

If run externally, this app will connect to OBS Studio over Websocket in
order to add the requested scenes. Configure it by adding something like
this to instance/config.py:

    OBS_WEBSOCKET = {
      'hostname': 'localhost',
      'port': 4444,
      'password': 'secret',
      }

Alternatively, you can install the **jw-meeting.py** script in OBS Studio
where it can use the scripting API to add the scenes. This mode seems less
stable at the moment.

Whichever mode you use, open http://localhost:5000/obs/ in a web browser
or create a browser dock with this URL in OBS.

There will be three tabs, for Meetings, Songs, and Videos. Clicking on the
link to one of these things will download the necessary material add each
item as a scene in OBS.

## Teaching Toolbox

This subapp is intended to help publishers witnessing by phone to quickly find
the online versions of the publications in the Teaching Toolbox.

First load the lists of publications:

  $ flask update magazines
  $ flask update books
  $ flask update videos

Then open http://localhost:5000/toolbox/ in a web browser.

## ePub Viewer

Download and display Epub files from JW.ORG in a web browser.

First load one or more of these lists:

  $ flask update study-pubs
  $ flask update magazines
  $ flask update books
  $ flask update videos

Then browser to http://localhost:5000/epub/

If you click on a link, you will get 404. To download the ePub file, note the last
element in the URL. This is the publication or issue code. Then run one of the
following commands:

  $ flask epub download-book **publications code**

or

  $ flask epub download-issue **issue code**

If the ePub viewer ever moves beyond the experimental state, we will implement
downloading of ePub files from the web interface.

## TODO

* Main chapter illustration not pulled from Happy Family

