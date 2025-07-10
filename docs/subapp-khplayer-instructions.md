# Instructions for KH Player, Zoom and OBS Studio

## Initial Setup

-   Turn on the TV.

-   Turn on the computer. There is no need to do anything at the login
    > prompt. After a short pause the desktop will appear.

-   Make sure an extension of the desktop has appeared on the TV as
    > well.

-   Double click on the **KH Player** icon on the desktop.

-   When **KH Player** appears, go to the **Actions** tab and click on
    > the **Start Meeting** button to launch Zoom and automatically log
    > in and start the meeting. Refrain from touch the mouse or keyboard
    > until the meeting window appears.

-   Click on **Start OBS**. Place the Zoom and OBS windows.

-   Go to **Zoom** and turn on the camera. Make sure the camera is set
    > to Dummy video device. If it will not turn on, see the
    > troubleshooting section below.

-    Unmute the microphone. Make sure it is set to **From-OBS**.

## Loading Meeting Media

-   Return to **KH Player** and switch to the **Meeting** tab. Click on
    > today's meeting. If it is not listed, press the **Refresh**
    > button.

-   A list of the media for the meeting will appear. Go to the bottom
    > and click on the **Download Media and Create Scenes in OBS**
    > button.

-   On Sunday go to the Songs tab and click on the button to load the
    > song selected by the speaker.

## Loading Clips from JW Stream

-   If you will be using material from JW Stream, go to the **Stream**
    > tab. If the program you need is not listed, press the **Refresh**
    > button.

-   Click on the required program. A player window will open.

-   Use the chapter buttons to go the the part of the program you need.
    > Use the time skip buttons to find the exact start point. Press the
    > **Set Start** button.

-   Use the time skip buttons to move to the end of the part you need.
    > Press the Set End button.

-   Fill in the clip name for future reference. Press the **Make Clip**
    > button. It will be downloaded in the background.

-   Repeat the above to make any additional clips required.

## Speaker's Slides

-   Insert a USB device with the speaker's slides. You can disconnect
    > the mouse. Avoid disconnecting the microphone or camera.

-   Drag the image files from the file manager window to the **Scenes**
    > tab of KH Player. A new scene will be created in OBS for each.

## Verification

-   Go to OBS and examine the scene list. Make sure everything needed is
    > there. Delete unneeded illustrations of videos. Switch to each
    > video (including the songs) and make sure the sound plays. Arrange
    > the scenes in the proper order.

-   If the sound for a video does not plays. If it does not go to the
    > troubleshooting guide below.

-   Switch to the **Stage** scene to make sure the camera is working. If
    > it is not, see the troubleshooting guide below.

-   Switch to the **Zoom** scene. It should show the active speaker. If
    > the active speaker is the virtual camera, the image will scrunch
    > up and go dark as the system swallows its tail. This is OK. If
    > anything else happens, refer to the troubleshooting guide.

## During the Meeting

-   At the start of the meeting, switch to the **Stage** scene in OBS.

-   When a song, video, or illustration is called for, switch to the
    > appropriate scene in OBS.

-   If someone will speak from Zoom, switch to the **Zoom** scene. If
    > you switch before he is the active speaker, it may show the wrong
    > person or a weird effect. Either wait or spotlight him.

-   If one participant in a demonstration will be on Zoom while the
    > other is in the Kingdom Hall, switch to the **Split Screen**
    > scene.

## Shutdown

-   Go to **OBS** and from the **Scene Collection** menu choose
    > **Remove**.

-   Stop the virtual camera and close OBS.

-   Close Zoom.

-   Turn off the computer.

-   Turn off the camera and close the lens cover.

-   Disconnect the microphone cable from the computer and roll it up so
    > it will not interfere with vacuuming.

## Troubleshooting Guide

### Image from camera is all black or has only backwards words

Make sure the camera is turned on and the lens cover is open.

### The image from the camera is frozen

This happens sometimes due to deficiencies of the drivers. To correct
it:

-   Pull the USB cable from the red Mirabox out of the computer.
    > Reinsert it.

-   Go to the **Actions** tab in **KH Player** and press the **Reconnect
    > Camera** button.

### The camera will not turn on in Zoom

-   Make sure the selected camera is **Dummy video device**.

-   Make sure the **Virtual Camera** is started in OBS.

### The TV shows the second Zoom window rather than the videos or lectern

> The full screen projector is not enabled in OBS. The easiest way to
> fix this is to go to the **Actions** tab in **KH Player** and press
> the **Start Projector** button.

### When you switch to the Zoom scene in OBS it fails to show the active speaker

Make sure the active speaker in Zoom really is what you expect. The
active speaker will be identified by a green border in the Gallery View.
If the expected speaker is not shown as active:

-   Make sure his microphone is unmuted

-   Prompt him to begin speaking

-   If the green border still does not move, right click and choose
    > Highlight.

If the correct speaker is highlighted in Zoom but still not shown in
OBS, go to the **Actions** tab in **KH Player** and press the
**Reconnect Zoom Capture** button.

### Sound from the microphone in the Kingdom Hall is not heard in Zoom

Check the following:

-   Make sure the microphone is plugged in and the light on it is on.

-   If the light is red, press the mute/unmute button next to the light
    > to unmute. The light should turn blue. If it does not, move to the
    > next step.

-   Go to the volume control on the computer's taskbar and make sure the
    > microphone is not muted there and that its volume is turned up
    > high enough.

-   Go to the Patchbay tab and make sure that sound from the microphone
    > is routed through the virtual audio cable to Zoom. If the
    > microphone was not yet plugged in when Zoom and OBS were started,
    > it will not be. If not, go to the **Actions** tab and press the
    > **Reconnect Audio** button.

### Sound from microphone as heard in Zoom is too soft

Check the following:

-   The microphone volume control on computer's taskbar.

-   The microphone volume in the **Audio Settings** in **Zoom**.

-   Try turning on **Automatically adjust microphone volume**.

-   Move the microphone further away from the conductor (about one
    > meter) so as to reduce the difference in volume. This also seems
    > to improve the tonal quality for the conductor's voice.

### An individual video has no sound

Occasionally **OBS** will fail to connect the sound for a video. When
this happens, do the following:

-   Start the video playing in **OBS**.

-   Go to the Edit menu and choose **Advanced Audio Properties**.

-   Find the video in the list (it will generally be the only one
    > listed) and flip **Audio Monitoring** from **Monitor and Output**
    > to **Monitor Off** and back until sound is heard.

-   Close the Advanced Audio Properties window.

-   Click on the video file in the **Sources** panel so that the player
    > controls will appear.

-   Go back to the start of the video and play, now with sound.

### Echo is heard in Zoom while playing videos

This is generally because the microphone in the Kingdom Hall is picking
up too much sound from the TV. To remedy, do one of the following:

-   Press the button on top of the microphone to mute it.

-   Open the volume control on the taskbar and mute the microphone or
    > turn it down.

-   Go to the **Patchbay** tab in **KH Player**. Click on the cable from
    > the microphone to delete it. Later restore it by dragging the
    > microphone output to the input of the **From-OBS** node.

### Video sound is heard in the Kingdom Hall but not in Zoom

This means that OBS is playing directly to the TV bypassing its virtual
audio cable. The quickest way to fix this is to go to the **Actions**
tab in **KH Player** and press the **Reconnect Audio** button.

### Video sound is coming out of the laptop speakers rather than the TV

Go to the **Actions** tab in **KH Player** and press the **Reconnect
Audio** button.

### Comments from Zoom are much louder than the videos

-   Right click on the volume control on the taskbar and choose Audio
    > Settings

-   Go to the **Applications** tab

-   There will be two instances of **ZOOM VoiceEngine**. Find the one
    > with the musical note and turn it down a bit.
