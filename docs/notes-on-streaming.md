# Notes on Streaming From OBS to TV

## Setting Up RTSP Server Perl

Install RTSP Server Perl:

    $ sudo apt install rtsp-server-perl

Change /etc/default/rtsp-server-perl to:

    CLIENT_PORT=8554
    CLIENT_BIND=192.168.6.10
    SERVER_PORT=5554
    SERVER_BIND=127.0.0.1
    LOG_LEVEL=3
    EXTRA_OPTS=""

Restart:

    $ sudo systemctl restart rtsp-server-perl.service

Start streaming from OBS:

* Go to **Settings**, **Output**
* Switch the **Output Mode** to Custom
* Select the **Recording** tab
* Switch **Type** to **Custom Output (FFmpeg)**
* Switch **FFmpeg Output Type** to Output to URL
* Set the **File path or URL** to rtsp://localhost:5554/obs
* Set the **Container Format** to rtsp
* Press **Start Recording**

## Chromecast

So far we have not figured out how to stream from OBS to a Chromecast. These notes are from our attempt.

* VLC can stream V4L2 to Chromecast, but with a delay of around a minute
* [Google Cast](https://en.wikipedia.org/wiki/Google_Cast)
* https://hackernoon.com/the-chromecast-protocol-a-brief-look
* https://github.com/cast-web/protocol
* https://github.com/googlecast/CastReceiver/issues/47
* https://developers.google.com/cast/docs/debugging/cac_tool
* [Cast.js Chromecast Sender Library](https://github.com/castjs/castjs)
* [Cast All The Things](https://github.com/skorokithakis/catt)

## References

* [RTSP Server Perl](https://metacpan.org/dist/RTSP-Server)
* [MediaMTX](https://github.com/bluenviron/mediamtx) -- See notes for setting up OBS
* [FFmpeg Protocol Documentation](https://ffmpeg.org/ffmpeg-protocols.html)
