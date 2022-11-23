# Scripts for use With OBS and Zoom

The scripts described below are likely broken due to changes in **khplayer**
and OBS.

## OBS to Zoom

The **obs2zoom** script listens to events from OBS and activates screen sharing.
It actually shares the images from the second camera which is intended to be a virtual
camera fed from OBS.

## OBS Scripts

It is possible to run **khplayer** and **obs2zoom** inside of OBS.

1. In OBS-Studio go to **Tools**, **Scripts** and press the **Add** button.
2. Browse to the obs-scripts directory of this project.
3. Select the **khplayer.py** and **obs-to-zoom.py** scripts and press OK.
4. Select **khplayer.py** and enable it.
5. Select **obs-to-zoom.py** and set the mode to **Manual** or **When Playing**.

