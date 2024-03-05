# Programming Notes

These are notes on the libraries, API's and frameworks used in this project.

## Flask and Friends

* [The Pallets Projects](https://palletsprojects.com/)
* [Flask](https://flask.palletsprojects.com/)
* [Flashing Messages in Flask](https://www.askpython.com/python-modules/flask/flask-flash-method)
* [Wtforms](https://wtforms.readthedocs.io/en/3.0.x/)

## Turbo Flask

* [Turbo-Flask](https://github.com/miguelgrinberg/turbo-flask)
* [Flask-Sock](https://github.com/miguelgrinberg/flask-sock)
* [Pure Python & Flask server-side event source](https://gist.github.com/jelmervdl/5a9861f7298907179c20a54c0e154560)
* [Server-sent events in Flask without extra dependencies](https://github.com/MaxHalford/flask-sse-no-deps)
* [Hotwire Turbo Express](https://github.com/twelve17/hotwire-turbo-express) -- For server-side Javascript, but good docs on Hotwire Turbo

## Javascript API's

* [JavaScript FormData](https://www.javascripttutorial.net/web-apis/javascript-formdata/)
* [Async Form Posts With A Couple Lines Of Vanilla JavaScript](https://pqina.nl/blog/async-form-posts-with-a-couple-lines-of-vanilla-javascript/)
* [Server-Sent Events: the alternative to WebSockets you should be using](https://germano.dev/sse-websockets/)
* [HTML Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)
* [Dragging OS Folders to Webpage](https://stackoverflow.com/questions/3590058/does-html5-allow-drag-drop-upload-of-folders-or-a-folder-tree)
* [Dragging to Reorder a List](https://stackoverflow.com/questions/10588607/tutorial-for-html5-dragdrop-sortable-list)

## Web Apps on the Desktop

* [PyWebview](https://github.com/r0x0r/pywebview)
* [UTF-8 Mode](https://peps.python.org/pep-0540/)
* [ZipApp](https://docs.python.org/3/library/zipapp.html)

## FFmpeg

* [FFmpeg](https://ffmpeg.org/)
* [How to Trim and Reencode Video Files](http://tech-for-teaching.nuhub.net/howto/trim-video/)
* [How to extract 1 screenshot for a video with ffmpeg at a given time?](https://stackoverflow.com/questions/27568254/how-to-extract-1-screenshot-for-a-video-with-ffmpeg-at-a-given-time)

Black detection using FFmpeg:

    $ ffmpeg -i clip.mp4 -vf blackdetect=d=0.1:pix_th=.1 -f rawvideo -y /dev/null

## Face Detection

* [Build Your Own Face Recognition Tool With Python](https://realpython.com/face-recognition-with-python/)
* [Face-Recognition](https://pypi.org/project/face-recognition/)

## Bible

* [Linkture](https://github.com/erykjj/linkture) -- parse Scripture references in multiple languages

## Epub

* [HTML to Epub](https://github.com/macgregor/html_to_epub)

## Sqlite3

* [The SQLite OS Interface or "VFS"](https://www.sqlite.org/vfs.html)
* [sqlite-s3vfs](https://github.com/uktrade/sqlite-s3vfs/)
* [s3vfs.py](https://gist.github.com/simonwo/b98dc75feb4b53ada46f224a3b26274c)

