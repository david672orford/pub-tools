# Pub-Tools

Pub-Tools is a Python-Flask app for downloading and displaying publications
from JW.ORG.

## Installing Pub-Tools

To install on Ubuntu and other Debian-Family Linuxes:

    $ sudo apt-get install git python3-pip ffmpeg python3-ewmh
    $ git clone https://github.com/david672orford/pub-tools.git
    $ cd pub-tools
    $ pip3 install -r requirements.txt
	$ mkdir instance
	$ echo "SECRET_KEY='`dd if=/dev/random bs=32 count=1 | base64`'" >>instance/config.py

## Running Pub-Tools

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser:

     http://localhost:5000

## Subapps

When you open Pub-Tools in a web browser, you will see a menu of subapps.
Each of them requires some setup before they will work. Refer to the
documentation below.

* [KH Player](docs/subapp-khplayer.md)
* [Teaching Toolbox](docs/subapp-toolbox.md)
* [Epub Reader](docs/subapp-epubs.md)

