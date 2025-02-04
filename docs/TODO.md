# Pub-Tools TODO

## Bugs

* Click on thumbnail in scenes list (sometimes) does nothing.
  (This is likely the case only after a refresh or the thumbnail.)
* Why no thumbnail if slide folder contains only a single video? (See talk №90)
* Straighten out the downloading of PDF thumbnails from Gdrive
* patchbay: it is possible to drop a node onto an input provoking an error in the javascript console
* filesytemencoding problems when started from khplayer-server.py (See https://docs.python.org/3/library/sys.html#sys.getfilesystemencoding)
* Some Gdrive sharing URL's not acceptable for pulling JW Stream URL lists?

## Easy Improvements

* Listen address and port setting in khplayer-server.py
* Verify cache cleaning policy and file categorization
* Add cleaners for gdrive-cache and flask-cache
* Progress bar for Gdrive downloads. This will require knowing the file size. (may already be done)

## Hard Stuff

* Figure out to set up logging better:
  * **flask cable** commands call logger.info(), but no output is produced
  * CLI support for enabling debugging per module
* Incorporate [Linkture](https://github.com/erykjj/linkture)
* Send scene reorder events to other (all) browsers
* Auto-assign F-keys to scenes and show then in the Scenes tab (may not be supported in OBS-Websocket)

## Reference for Possible Future Projects

* https://basilchackomathew.medium.com/face-recognition-in-python-a-comprehensive-guide-960a48436d0f
* https://stackoverflow.com/questions/384759/how-do-i-convert-a-pil-image-into-a-numpy-array#384926
* https://towardsdatascience.com/lightning-fast-video-reading-in-python-c1438771c4e6
* [FFmpeg Scene selection : extracting iframes and detecting scene change](https://www.bogotobogo.com/FFMpeg/ffmpeg_thumbnails_select_scene_iframe.php)
* [Audio-Visual Speaker Detection](https://medium.com/@siddheshdeshpande/audio-visual-active-speaker-detection-on-video-for-ai-tools-dc297443f0be)
* [Speaker Identification](https://speechbrain.readthedocs.io/en/latest/tutorials/basics/what-can-i-do-with-speechbrain.html)
* [Git in Python](https://stackoverflow.com/questions/13166595/how-can-i-pull-a-remote-repository-with-gitpython#13166781)

## OBS Docs to Improve

* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting)
