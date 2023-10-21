## The KH Player Module

This is the most well-developed of the modules. It helps you to load the videos
and illustrations for a congregation meeting into OBS Studio ready to play.

The KH Player module communicates with OBS over websocket. You will need to use
OBS version 2.8 or later. To pair them, open OBS and enable the websocket plugin.
Note the port and password. Then open **instance/config.py** in a text editor and
add this:

    OBS_WEBSOCKET = {
      'hostname': 'localhost',
      'port': 4455,
      'password': 'secret',
      }

Replace *secret* with the password you set for the Websocket plugin in OBS.

Start the Pub-Tools web server:

    $ ./start.py

Then open this URL in a web browser:

    http://localhost:5000/toolbox/

A window will appear with tabs such as **Meetings**, **Songs**,
and **Videos** which can be used to load videos material into OBS.

## OBS Scripts

The obs-scripts directory contains scripts which can be installed in OBS studio
to automate tasks required when using it at a congregation meeting.

### khplayer.py

This script runs the Pub Tools appliation web server into OBS Studio. This means
that there is no need to start it separately.

### virtual-audio-cable.py

This script creates two virtual audio cables in the Pipewire audio server and
connect them properly to feed the output of OBS Studio and the microphone into the
speakers also selected in KH Player. The microphone and speakers are selected in
KH Player in the **Audio** tab.

### autostart-outputs.py

This script starts the virtual camera and a fullscreen output on the monitor selected in
the script configuration screen. This saves time when getting things set up before
a congregation meeting.

### auto-mute.py

This script mutes the microphone when music or videos are playing. This improves sound
quality for participant in Zoom considerably.

This script also initiates a scene switch to the first scene whenever it detects that
the music or video has finished. To get the desired effect, you should make sure that
the first scene shows the stage.

