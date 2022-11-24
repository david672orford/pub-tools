# Programming Notes

These are notes on the libraries, API's and frameworks used in this project.

## Flask

* [The Pallets Projects](https://palletsprojects.com/)
* [Flask](https://flask.palletsprojects.com/)
* [Turbo-Flask](https://github.com/miguelgrinberg/turbo-flask)
* [Flask-Sock](https://github.com/miguelgrinberg/flask-sock)
* [Flashing Messages in Flask](https://www.askpython.com/python-modules/flask/flask-flash-method)
* [Pure Python & Flask server-side event source](https://gist.github.com/jelmervdl/5a9861f7298907179c20a54c0e154560)

## Javascript API's

* [JavaScript FormData](https://www.javascripttutorial.net/web-apis/javascript-formdata/)
* [Async Form Posts With A Couple Lines Of Vanilla JavaScript](https://pqina.nl/blog/async-form-posts-with-a-couple-lines-of-vanilla-javascript/)
* [Server-Sent Events: the alternative to WebSockets you should be using](https://germano.dev/sse-websockets/)

## Web Apps on the Desktop

* [PyWebview](https://github.com/r0x0r/pywebview)

## FFmpeg

* [FFmpeg](https://ffmpeg.org/)
* [How to Trim and Reencode Video Files](http://tech-for-teaching.nuhub.net/howto/trim-video/)


Black detection using FFmpeg:

    $ ffmpeg -i clip.mp4 -vf blackdetect=d=0.1:pix_th=.1 -f rawvideo -y /dev/null

