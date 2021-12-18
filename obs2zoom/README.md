# obs2teams

## Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install the Video For Linux Loopback Device

    $ sudo apt install v4l2loopback-dkms

## Install OBS-Websocket Module Version 0.4.1

OBS-Websocket is needed only if you play to run the external tool version.
It is not needed if you plan to run obs2zoom inside OBS Studio as a script.

    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
    $ sudo apt install -f

## Run External Tool Version

1. Enable OBS-Websocket
2. Start **bin/obs2zoom**.
3. Start a conference in Zoom
4. Start the virtual camera. Screen sharing will start.

If you start **bin/obs2zoom** with the **--auto** option, then screen sharing
in Zoom will not start immediately when you enable the virtual camera. It will
only start if a video is playing or an image is in the scene. If you switch
away from the scene or the video ends, screen sharing will be stopped.

## Run as a OBS Studio Script

In OBS-Studio go to **Tools**, **Scripts** and press the **Add** button.
Find the **obs2zoom.py** script and press **OK**. In its options screen
enable it by setting the mode to **Manual** or **When Playing**.

