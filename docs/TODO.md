# Pub-Tools TODO

## Bugs

* Click on thumbnail in scenes list (sometimes) does nothing.
  (This is likely the case only after a refresh or the thumbnail.)
* Why no thumbnail if slide folder contains only a single video? (See talk №90)
* patchbay: it is possible to drop a node onto an input provoking an error in
  the javascript console
* patchbay: nodes jump slightly on reload
* Problems with Unicode filenames on Windows when started from khplayer-server.py.
  (See https://docs.python.org/3/library/sys.html#sys.getfilesystemencoding)
* Yeartext slide uses fonts not available on Windows.
* Yeartext slide uses Roboto font which is not necessarily installed on
  Ubuntu. Use fc-list to detect problem.
* Playing video in pywebview requires packages which are not necessarily
  installed in Ubuntu. See
  https://askubuntu.com/questions/1350001/how-to-use-gstreamer-to-play-an-mp4-video

## Easy Improvements

* Highlight current meeting
* Progress bar for Gdrive downloads. This will require knowing the file size.
  (may already be done)

## Hard Stuff

* Figure out to set up logging better:
  * **flask cable** commands call logger.info(), but no output is produced
  * CLI support for enabling debugging per module
* Incorporate [Linkture](https://github.com/erykjj/linkture)
* When the user change the position of a scene by dragging and dropping send
  custom event to the other browsers to they can move it too
* Auto-assign F-keys to scenes and show then in the Scenes tab (may not be supported in OBS-Websocket)

## Reference for Possible Future Projects

* https://basilchackomathew.medium.com/face-recognition-in-python-a-comprehensive-guide-960a48436d0f
* https://stackoverflow.com/questions/384759/how-do-i-convert-a-pil-image-into-a-numpy-array#384926
* https://towardsdatascience.com/lightning-fast-video-reading-in-python-c1438771c4e6
* [FFmpeg Scene selection : extracting iframes and detecting scene change](https://www.bogotobogo.com/FFMpeg/ffmpeg_thumbnails_select_scene_iframe.php)
* [Audio-Visual Speaker Detection](https://medium.com/@siddheshdeshpande/audio-visual-active-speaker-detection-on-video-for-ai-tools-dc297443f0be)
* [Speaker Identification](https://speechbrain.readthedocs.io/en/latest/tutorials/basics/what-can-i-do-with-speechbrain.html)

## OBS Docs to Improve

* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting)
