# Running JW Meeting and OBS to Zoom

## Install OBS Studio

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install obs-studio

## Install the Video For Linux Loopback Device

    $ sudo apt install v4l2loopback-dkms

## Install OBS-Websocket Module Version 0.4.1

OBS-Websocket is needed only if you play to run JW-Pubs or OBS to Zoom
from outside of OBS. It is not required when they are installed in OBS as
scripts where they can communicate with OBS directly using its API.

    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
    $ sudo apt install -f

## Run External Tool Versions

1. Enable OBS-Websocket
2. Start **start.py** from the directory above.
2. Start **obs-to-zoom.py**.
3. Start a conference in Zoom
4. Start the virtual camera. Screen sharing will start.

If you start **obs-to-zoom.py** with the **--auto** option, then screen sharing
in Zoom will not start immediately when you enable the virtual camera. It will
only start if a video is playing or an image is in the scene. If you switch
away from the scene or the video ends, screen sharing will be stopped.

## Run as a OBS Studio Scripts

1. In OBS-Studio go to **Tools**, **Scripts** and press the **Add** button.
2. Browse to the obs-scripts directory of this project.
3. Select the jw-meeting.py and obs-to-zoom.py scripts and press OK.
4. Select jw-meeting.py and enable it.
5. Select obs-to-zoom.py and set the mode to **Manual** or **When Playing**.

