# The Teaching Toolbox Module

This subapp displays a list of the publications from the Teaching Toolbox
along with the link to it on JW.ORG. It is intended to help publishers
to send links to interested persons.

Before using this module, load the lists of publications:

    $ flask jworg periodicals wp all
    $ flask jworg periodicals g all
    $ flask jworg books
    $ flask jworg videos VODMinistry VODMinistryTools

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser:

    http://localhost:5000/toolbox/

