# Scripts for use With OBS and Zoom

The scripts described below are likely broken due to changes in **khplayer**
and OBS.

## OBS to Zoom

The **obs-to-zoom.py** script listens to events from OBS and activates screen
sharing. It actually shares the images from the second camera which is
intended to be a virtual camera fed from OBS.

This script can be run outside of OBS as long as the websocket 4.x plugin
installed and enabled:

  $ ./obs-to-zoom.py

This script can be run inside OBS:

1. In OBS-Studio go to **Tools**, **Scripts** and press the **Add** button.
2. Browse to the obs-scripts directory of this project.
3. Select the **obs-to-zoom.py** script and press OK.
4. Select **obs-to-zoom.py** and enable it.
4. Select **obs-to-zoom.py** and set the mode to **Manual** or **When Playing**.

## KH Player

It is possible to run **khplayer** inside of OBS.

1. In OBS-Studio go to **Tools**, **Scripts** and press the **Add** button.
2. Browse to the obs-scripts directory of this project.
3. Select the **khplayer.py** script and press OK.
4. Select **khplayer.py** and enable it.
5. Add a browser dock with a a URL of http://localhost:5000/khplayer/meetings/

