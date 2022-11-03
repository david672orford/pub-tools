# JW-Pubs

This is a Python-Flask app for downloading and displaying publications from
JW.ORG. It is divided into a number of modules which can be enabled and
disabled individually in the config file.

## Install

    $ sudo apt-get install python3-pip
    $ pip3 install flask flask-sqlalchemy

## Teaching Toolbox

This subapp is intended to help publishers witnessing by phone to quickly find
the online versions of the publications in the Teaching Toolbox. 

## JW-Meeting and OBS to Zoom

This app helps you to load the vidoes and illustrations for a meeting into OBS
Studio. If run externally, it will try to connect to OBS Studio over 
Websocket on order to add the requested scenes. Alternatively, you can install
the **jw-meeting.py** script in OBS Studio where it can use the scripting
API to add the scenes. This is also more convenient because the web server
is started automatically whenever OBS Studio starts.

## Epub Viewer

Download and display Epub files from JW.ORG in a web browser.

## TODO

* Main chapter illustration not pulled from Happy Family

