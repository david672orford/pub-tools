# Pub-Tools TODO

## Bugs

* Is there a scenario in which /patchbay/create-link fails to post values? We have seen:
    KeyError: 'output_port_id'
* Click on thumbnail in scenes list (sometimes) does nothing

## Easy Improvements

* Incorporate [Linkture](https://github.com/erykjj/linkture)
* Validate configuration
  * https://docs.python-cerberus.org/
  * https://github.com/python-jsonschema/jsonschema
  * https://json-schema.org/learn/getting-started-step-by-step

## Hard Stuff

* Limit Bible Study illustrations to paragraph range stated in fragment. This may
be difficult because it seems the Workbook sometimes excludes the paragraph
with the illustration if it is at the beginning (or perhaps the end).
* Auto-assign F-keys to scenes and show then in the Scenes tab (may not be supported in OBS-Websocket)
* Auto-create yeartext slide (need to find online source)

## For the future

* https://basilchackomathew.medium.com/face-recognition-in-python-a-comprehensive-guide-960a48436d0f
* https://medium.com/@siddheshdeshpande/audio-visual-active-speaker-detection-on-video-for-ai-tools-dc297443f0be
* https://towardsdatascience.com/lightning-fast-video-reading-in-python-c1438771c4e6
* [FFmpeg Scene selection : extracting iframes and detecting scene change](https://www.bogotobogo.com/FFMpeg/ffmpeg_thumbnails_select_scene_iframe.php)

## OBS Docs to Improve

* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting)

