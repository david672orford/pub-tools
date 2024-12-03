# The Teaching Toolbox Module

This subapp displays a list of the publications from the Teaching Toolbox
along with the link to it on JW.ORG. It is intended to help publishers
to send links to interested persons.

Before using this module, load the lists of publications:

    $ flask jworg update-periodicals wp all
    $ flask jworg update-periodicals g all
    $ flask jworg update-books
    $ flask jworg update-videos VODMinistry VODMinistryTools

Start the Pub-Tools web server:

    $ ./start.py

On Microsoft Windows:

    > python start.py

Then open this URL in a web browser:

    http://localhost:5000/toolbox/
