# obs2teams

## Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install OBS Websocket Module Version 0.4.1

    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
    $ sudo apt install -f

## Install the Video For Linux Loopback Device

    $ sudo apt install v4l2loopback-dkms

