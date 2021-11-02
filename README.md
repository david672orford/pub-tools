This is a simple Python-Flask app which visits JW.ORG and gets a list
of the books, magazines, and videos available. It then displays very
simple lists with links back to JW.ORG.

# JW-Meeting

This set of tools was created during the COVID-19 pandemic to make it easier
to download and play videos and illustrations used in the two weekly meetings
held by Jehovah's Witnesses. The videos are loaded into OBS Studio for playing.
Zoom screen sharing is started and stopped automatically. OBS plays through
its virtual camera which Zoom sees as a second camera.

## Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install the Video For Linux Loopback Device

    $ sudo apt install v4l2loopback-dkms

## Install OBS Websocket

    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
    $ sudo apt install -f
    $ pip3 install obs-websocket-py

## Start JW-Meeting

    $ ./start.py

