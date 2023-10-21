# The Epub Viewer Module

This is an experimental framework for downloading and viewing Epub files
from JW.ORG in a web browser.

To see what it can do so far, first run one or more of the following commands
to download the lists of available publications:

    $ flask update magazines
    $ flask update books

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser to see the list of publications:

    http://localhost:5000/epubs/

If you click on a link, you will get 404. To download the ePub file, note the
publication code which is the last component of the URL path. Then run this
command:

    $ flask epub download **pub code**

If the ePub Viewer module ever moves beyond the experimental state, we will
add a button or other control for downloading the ePub files directly from
the web interface.

