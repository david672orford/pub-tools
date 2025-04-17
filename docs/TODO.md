# Pub-Tools TODO

## Bugs

* Click on thumbnail in scenes list (sometimes) does nothing.
  (This is likely the case only after a refresh of the thumbnail.)
* Why no thumbnail if slide folder contains only a single video? (See talk №90)
* Playing video in pywebview doesn't work on some Ubuntu machines. Why?
* Exception thrown on expired Jwstream links.
* Face detection sometimes gets horizontal position wrong (difficult to reproduce)
* Progress when media file downloaded from inside playlist on Google Drive.
  (Downloading an MP4 file from the Google Drive itself does show progress.
  Download from within a zip playlist does not seem to.)
* Problems with Unicode filenames on Windows when started from khplayer-server.py.
  (See https://docs.python.org/3/library/sys.html#sys.getfilesystemencoding)
* Close sound settings after save fails

## Hard Stuff

* Load Bible verses. Could incorporate [Linkture](https://github.com/erykjj/linkture).
* Figure out how to set up Python logging better:
  * **flask cable** commands call logger.info(), but no output is produced
  * CLI support for enabling debugging per module
* When the user change the position of a scene by dragging and dropping send
  custom event to the other browsers so they can move it too
* Auto-assign F-keys to scenes and show then in the Scenes tab (may not be supported in OBS-Websocket)
* Integration with Jitsi Meet

## OBS Docs to Improve

* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting)
