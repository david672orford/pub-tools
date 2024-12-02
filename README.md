# Pub-Tools

Pub-Tools is a Python-Flask app for downloading and displaying publications
from JW.ORG.

## Installing Pub-Tools

To install on Ubuntu and other Debian-Family Linuxes:

    $ sudo apt-get install git cmake ffmpeg pulseaudio-utils python3-pip python3-venv
    $ git clone https://github.com/david672orford/pub-tools.git
    $ cd pub-tools
    $ ./venv_tool.py --create

To install on Microsoft Windows: (draft)

    > winget install python
    > winget install --id Git.Git -e --source winget
    > winget install cmake
    > winget install --id Microsoft.VisualStudio.2022.Community
    (Open new terminal)
    > git clone https://github.com/david672orford/pub-tools.git
    > cd pub-tools
    > python3 venv_tool.py --create

To switch the UI to Russian:

    $ cd app/translations
    $ make mo
    $ cd ../..
    echo 'UI_LANGUAGE="ru"' >>instance/config.py

To change the publication language to Russian:

    $ echo 'PUB_LANGUAGE="ru"' >>instance/config.py

## Running Pub-Tools

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser:

    http://localhost:5000

## Subapps

When you open Pub-Tools in a web browser, you will see a menu of subapps.
Each of them requires some setup before it will work. Refer to the
documentation below.

* [KH Player](docs/subapp-khplayer.md)
* [Teaching Toolbox](docs/subapp-toolbox.md)
* [Epub Reader](docs/subapp-epubs.md)
