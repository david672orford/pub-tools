# JW-Pubs

This is a set of Python-Flask apps for downloading and displaying
publications from JW.ORG.

## Teaching Toolbox

This app displays pages with links to the publications in the Teaching
Toolbox on JW.ORG.

## JW-Meeting

This app helps you to load the vidoes and illustrations for a meeting
into OBS Studio.

## Epub Viewer

Download and display Epub files from JW.ORG in a web browser.

## OBS2Zoom

This utility watches events from OBS Studio and starts and stops Zoom
screen sharing as appropriate. It is available in two versions. One is
a command-line program which connects to OBS Studio using Websocket to
read the events. The other version is an OBS script which gets the
events using the OBS scripting API.

## Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install OBS Websocket

    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
    $ sudo apt install -f
    $ pip3 install obs-websocket-py

