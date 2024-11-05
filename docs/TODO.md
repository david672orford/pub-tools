# Pub-Tools TODO

## Bugs

* Click on thumbnail in scenes list (sometimes) does nothing. (This is likely after a refresh.)
* Why no thumbnail if slide folder contains only a video? (See no90)

## Easy Improvements

* Verify cache cleaning policy and file categorization
* Add cleaners for gdrive-cache and flask-cache
* CLI support for enabling debugging by module
* Progress bar for Gdrive downloads. This will require knowing the file size. (make sure this is finished)
* Validate configuration
    * https://docs.python-cerberus.org/
    * https://github.com/python-jsonschema/jsonschema
    * https://json-schema.org/learn/getting-started-step-by-step
* Incorporate [Linkture](https://github.com/erykjj/linkture)

## Hard Stuff

* Send scene reorder events to other browsers
* Auto-assign F-keys to scenes and show then in the Scenes tab (may not be supported in OBS-Websocket)
* Auto-create yeartext slide (would need to find the current yeartext somewhere on JW.ORG)
* Better Zoom capture by capturing the whole window and producing automatic crops to the current
  speaker and the current and previous speakers.

## For the Future

* https://basilchackomathew.medium.com/face-recognition-in-python-a-comprehensive-guide-960a48436d0f
* https://medium.com/@siddheshdeshpande/audio-visual-active-speaker-detection-on-video-for-ai-tools-dc297443f0be
* https://towardsdatascience.com/lightning-fast-video-reading-in-python-c1438771c4e6
* [FFmpeg Scene selection : extracting iframes and detecting scene change](https://www.bogotobogo.com/FFMpeg/ffmpeg_thumbnails_select_scene_iframe.php)

## OBS Docs to Improve

* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting)

