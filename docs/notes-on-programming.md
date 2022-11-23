# Programming Notes

These are notes on the libraries, API's and frameworks used in this project.

## Flask

* [Flashing Messages in Flask](https://www.askpython.com/python-modules/flask/flask-flash-method)
* [Pure Python & Flask server-side event source](https://gist.github.com/jelmervdl/5a9861f7298907179c20a54c0e154560)

## Javascript API's

* https://www.javascripttutorial.net/web-apis/javascript-formdata/
* https://pqina.nl/blog/async-form-posts-with-a-couple-lines-of-vanilla-javascript/
* https://germano.dev/sse-websockets/

## Web Apps on the Desktop

* [PyWebview](https://github.com/r0x0r/pywebview)

## FFmpeg

* https://pypi.org/project/python-ffmpeg/
* https://superuser.com/questions/326629/how-can-i-make-ffmpeg-be-quieter-less-verbose

Black detection using FFmpeg:

    $ ffmpeg -i clip.mp4 -vf blackdetect=d=0.1:pix_th=.1 -f rawvideo -y /dev/null

