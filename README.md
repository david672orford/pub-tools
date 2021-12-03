# JW-Pubs

This is a set of Python-Flask apps for downloading and displaying
publications from JW.ORG.

## Teaching Toolbox

This app displays pages with links to the publications in the Teaching
Toolbox on JW.ORG.

## JW-Meeting

This app helps you to load the vidoes and illustrations for a meeting
into OBS Studio.

### Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

### Install OBS Websocket

    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
    $ sudo apt install -f
    $ pip3 install obs-websocket-py

