# Notes on Streaming to TV

## MediaMTX

https://github.com/bluenviron/mediamtx

### Working in OBS Stream Mode

* srt://localhost:8890/?streamid=publish:obs (2-3 seconds)

### Working in OBS Record Mode

* rtsp://localhost:8554/obs (< 1 second)

## Chromecast

* VLC can stream V4L2 to Chromecast, but with a delay of around a minute
* [Google Cast](https://en.wikipedia.org/wiki/Google_Cast)
* https://hackernoon.com/the-chromecast-protocol-a-brief-look
* https://github.com/cast-web/protocol
* https://github.com/googlecast/CastReceiver/issues/47
* https://developers.google.com/cast/docs/debugging/cac_tool
* [Cast.js Chromecast Sender Library](https://github.com/castjs/castjs)
* [Cast All The Things](https://github.com/skorokithakis/catt)

## FFMpeg

* https://ffmpeg.org/ffmpeg-protocols.html
