# Notes on OBS Studio

* [OBS Main Site](https://obsproject.com/)
* [OBS Github Site](https://github.com/obsproject/obs-studio)
* [OBS Discord Channel](https://discord.com/channels/348973006581923840/636682839382949888)
* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Build Instructions for Linux](https://github.com/obsproject/obs-studio/wiki/build-instructions-for-linux)
* [Building on Debian (from forum)](https://obsproject.com/forum/threads/debian-obs-studio-build-mini-howto.169680/)
* [Checking out Pull Requests](https://stackoverflow.com/questions/27567846/how-can-i-check-out-a-github-pull-request-with-git#30584951)
* [Debian OBS Studio Build Mini-HOWTO](https://obsproject.com/forum/threads/debian-obs-studio-build-mini-howto.169680/)

## OBS Studio Installation

On Ubuntu:

    $ sudo add-apt-repository ppa:obsproject/obs-studio
    $ sudo apt install ffmpeg obs-studio

On Microsoft Windows:

    $ winget install -e --id OBSProject.OBSStudio

## Integration of OBS Studio with other Programs

Video and audio can be fed into and out of OBS using the virtual camera,
virtual audio cables, streaming protocols, and media players embeded in
browser sources.

* [How to Use OBS with Zoom](https://www.eigenmagic.com/2020/04/22/how-to-use-obs-studio-with-zoom/) -- Instruction for connecting OBS and Zoom using a V4L virtual camera on Ubuntu Linux
* [VDO.Ninja](https://docs.vdo.ninja/) -- Browser-based videoconferencing designed for integration with OBS
* [Send SRT Video from OBS to OBS without a Server](https://youtu.be/eDgZ-IqvCJc?si=jGq48syIcpUk4IIL) -- SRT is a streaming format which can connect programs
* [SRT Protocol Streaming Guide](https://obsproject.com/kb/srt-protocol-streaming-guide)

### SRT Instructions

* On Receiving end
    * Create a media source
    * Turn off **Local file**
    * Turn off **Restart playback when source becomes active**
    * Set **Input** to an SRT URL such as srt://192.168.0.1:4000?mode=listener
    * Set the **Input format** to "mpegts"
* Go to the other OBS and open settings
    * Under **Stream** change the **Service** to Custom
    * Set the **Server** to an SRT URL such as srt://192.168.6.251:4000
    * Save settings
    * Press **Start Streaming**

The above has about three seconds of latency. To get down to about half a second:

* Go to **Settings**, **Output** on the sender
* Change the **Output Mode** to Custom
* Switch to the **Recording** tab
* Change **FFmpeg Output Type** to Output to URL
* Set the **File path or URL** to the caller URL used above
* Set the **Container Format** to mpegts
* Check the box **Show all codecs (even if potentially incompatible)
* Set the **Video Encoder** to libx264
* Save the settings
* Press **Start Recording**

## OBS-Websocket

OBS-Websocket is a plugin for OBS (now included in the official packages) which allows an external
program to learn its state and control it. Controlling OBS through a websocket is often easier
than writing a plugging or a script to run inside OBS.

* [Github Site](https://github.com/obsproject/obs-websocket)
* [Protocol](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md)
* [Plugin Example](https://github.com/obsproject/obs-websocket/blob/eed8a49933786383d11f4868a4e5604a9ee303c6/lib/example/simplest-plugin.c)
* [OBS-Web](https://github.com/Niek/obs-web) -- a remote control which uses OBS-Websocket

Requests missing from OBS-Websocket:

* Get the UUID of a scene
* Create a group
* Get the UUID of a group
* Get properties of an object (source, output, etc.) kind without instantiating it
* Get locale
* Get dark mode

## OBS Script Development

OBS embeds Lua and Python interpreters. Scripts written in these language can automate
tasks, be sources and sinks of video and audio, and perform filtering. Python scripts
do not generally run fast enough to process video, but Lua scripts do.

* [Python/Lua Scripting](https://docs.obsproject.com/scripting) -- Description of the functions which a script should apply and how it calls the C API
* [API Reference](https://docs.obsproject.com/reference-core-objects) -- Scripts call this C API through wrappers
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting) -- Wiki page with more information about the funtions a script must provide
* [Python Scripting Cheatsheet](https://github.com/upgradeQ/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API) -- Examples of using the API from Python
* [Cheat Sheet for Creating Scenes and Scene Items Functions in Lua](https://github.com/Chriscodinglife/get-started-with-lua) -- Examples of using the API from Lua
* [Tips and Tricks for Lua Scripts](https://obsproject.com/forum/threads/tips-and-tricks-for-lua-scripts.132256/) -- OBS Forum thread

### Example OBS Scripts

* [Scripts Forum](https://obsproject.com/forum/resources/categories/scripts.5/) -- Place for people to post their scripts
* [OBS-Libre-Macros](https://github.com/upgradeQ/obs-libre-macros) -- Framework for attaching Lua scripts to sources. Includes some interesting examples.
* [Scripting Tutorial Source Shake](https://obsproject.com/wiki/Scripting-Tutorial-Source-Shake) -- Animate the scene item transform in Python or Lua
* Video filters written in LUA and shader language
    * [Scripting Tutorial Halftone Filter](https://obsproject.com/wiki/Scripting-Tutorial-Halftone-Filter)
    * [Pan Zoom Rotate Filter](https://obsproject.com/forum/resources/pan-zoom-rotate.1489/)
    * [RGB Adjustment Filter](https://obsproject.com/forum/resources/rgb-adjustment-tool-filter.1642/ )
* [Lua Color Source](https://obsproject.com/forum/resources/lua-color-source.717/) -- Solid color video source using drawing commands
* [JW Timer](https://github.com/lucidokr/obs-jw-timer/) -- Countdown timer in a text source
* [Projector Hotkeys](https://obsproject.com/forum/resources/projector-hotkeys.1197/) [Github](https://github.com/DavidKMagnus/projector-hotkeys) -- Create new hotkey actions
* Screenshotting
    * [Advanced Filename Formatter](https://github.com/Penwy/adv-ff)
    * [Get source frame data](https://obsproject.com/forum/threads/tips-and-tricks-for-lua-scripts.132256/page-2#post-515653)
    * [Get source frame data FFI](https://github.com/KashouC/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API/blob/master/src/get_source_frame_data_ffi.py)
    * [PR: Typemapping for gs_stagesurface_map added](https://github.com/obsproject/obs-studio/pull/4779)

## OBS Plugin Development

* [Plugin API Docs](https://obsproject.com/docs/plugins.html) -- Describes plugin template and how to register the sources, outputs, etc. which one's plugin provides
* [OBS-V4L2Sink](https://github.com/CatxFish/obs-v4l2sink) -- Useful as example of an output plugin
* [OBS Source Record](https://github.com/exeldro/obs-source-record) -- Example of filter which reads frame data
* [OBS Face Tracker](https://github.com/norihiro/obs-face-tracker) -- Another example of a filter which reads frame data

### Useful-Looking OBS Plugins

* [OBS Studio Portable](https://github.com/wimpysworld/obs-studio-portable) -- OBS Studio built with 50 additional plugins
* [Advanced Scene Switcher](https://obsproject.com/forum/resources/advanced-scene-switcher.395/) [Github](https://github.com/WarmUpTill/SceneSwitcher) -- Automatically triggered macros automate tasks
* [Move Transition](https://obsproject.com/forum/resources/move.913/) [Github](https://github.com/exeldro/obs-move-transition) -- Smoothly moves and resizes common items during scene transitions
* [Transitions Table](https://obsproject.com/forum/resources/transition-table.1174/) [Github](https://github.com/exeldro/obs-transition-table) -- More or maybe better control over transitions between particular scenes
* [Source Dock](https://obsproject.com/forum/resources/source-dock.1317/) [Github](https://github.com/exeldro/obs-source-dock) -- Always show a particular source in UI
* [Downstream Keyer](https://github.com/exeldro/obs-downstream-keyer) -- Adds an overlay to all scenes
* [Shaderfilter](https://github.com/exeldro/obs-shaderfilter/) -- Write video filters in shader language
* [Background Removal](https://github.com/occ-ai/obs-backgroundremoval) -- Works, but not as well as Zoom's implementation
* [Virtual Background](https://github.com/kounoike/obs-virtualbg) -- Crashes
* [Some Plugins Under Development](https://obsproject.com/forum/threads/some-plugins-under-development.160557/) -- Whole collection of plugins which perform interesting and unusual functions
* [Pthread Text](https://obsproject.com/forum/resources/pthread-text.1287/) -- Text rendering using Pango
* [Source Clone](https://obsproject.com/forum/resources/source-clone.1632/) [Github](https://github.com/exeldro/obs-source-clone) -- Clone sources to allow different filters, clone current or previous scene
* [jrDockie](https://obsproject.com/forum/resources/jrdockie-save-and-load-window-and-dock-layouts.1955/) [Github](https://github.com/dcmouser/obsPlugins/tree/main/jr/jrdockie) -- Load and save browser dock sets. Has OBS-Websocket integration.

## Audio Output

OBS has an internal audio mixer. The output of this mixer is used when
streaming or recording to a file. However, there is no provision for
sending it to a local audio devices. For some reason the developers do
not regard this as a serious deficiency, to the considerable frustration
of quite a number of users.

* [Idea: Virtual Camera audio](https://ideas.obsproject.com/posts/1415/obs-virtual-camera-audio) -- Proposal to provide audio output
* [Idea: Additional 'Aux Send' / monitor channel, or 'Virtual Audio Output'](https://ideas.obsproject.com/posts/965/additional-aux-send-monitor-channel-or-virtual-audio-output)
* [PR: Virtual Camera Audio in Linux](https://github.com/obsproject/obs-studio/pull/8171) -- Uses ALSA loopback device
* [PR: linux-pulseaudio: Implement audio output](https://github.com/obsproject/obs-studio/pull/10495) -- Our implementation of audio output for Linux
* [PR: OBS Pipewire Audio Capture](https://github.com/dimtpap/obs-pipewire-audio-capture) -- Might be a good place to add audio output

## OBS Bugs We Are Following

* [Bug: Under OBS 30.0.0 CreateScene reverses the order of sequentially added scenes](https://github.com/obsproject/obs-websocket/issues/1181)
* [Bug: Disappearing Docks](https://www.reddit.com/r/obs/comments/114lnoj/disappearing_docks_how_do_i_get_them_back/)
* [Bug: Crash in File Picker](https://github.com/obsproject/obs-browser/issues/384)
* Bug: DND of file into browser dock does nothing, but DND of URL works
* [PR: linux-v4l2: Give camera up to 2 seconds to start](https://github.com/obsproject/obs-studio/pull/10335)
* [Bug: Browser Dock: Resize and DND signals become disconnected on Linux](https://github.com/obsproject/obs-browser/issues/437)
* [PR: Enable building with CEF 6261](https://github.com/obsproject/obs-browser/pull/434)
* [Lua: Deadlocks in scripts that implement video sources and call obs_enter_graphics](https://github.com/obsproject/obs-studio/issues/6674)
* [WHIP/WebRTC support missing on linux release](https://github.com/obsproject/obs-studio/issues/9484)

## Notes from Programming in OBS

Here are some notes on concepts and objects in OBS which we had to figure
out when writing scripts for it.

## Configuration

Configuration directory:

* %APPDATA%/obs-studio
* $HOME/.config/obs-studio

What is where:

* In global.ini aka appConfig
  * Location of profiles: Locations, Profiles
  * Location of scene collections: Locations, SceneCollections
  * Location of user.ini: Locations, Configuration
* In user.ini aka userConfig
* Show active outputs warning on exit: General, ConfirmOnExit=false
  * Python path (Windows): Python, Path64bit (path is in Windows format with forward slashes)
  * Full-height browser docks: BasicWindow, SideDocks
  * Browser dock configuration in BasicWindow, ExtraBrowserDocks
  * BasicWindow, ProjectorAlwaysOnTop=true
  * BasicWindow, CloseExistingProjectors=true
* In the Scene Collection
  * Addon scripts: modules, scripts-tool,
* In the profile
  * Hotkeys
  * Output settings
  * Audio monitor device selection

### Object Hierarcy

Each **Scene** has zero or more **Scene Items**. Each Scene Item has a **Source** to which it applies
a **Scene Item Transform**. A source is an **Input** or another Scene.

Scenes are identified by Name and by UUID. Scene Items are identified by Scene and ID.
Scene Item ID's are a small integers. They are unique only within the scene.

Each Scene Item also has an **Index** which determines its place in the stacking order
within the Scene. The index starts with 0. Stacking orders ascend from background to
foreground. However, they descend in the Sources Dock.

### Coordinate Transformation of Scene Items

The scaling and placement of images and videos in scenes is controlled by the
transform parameters. One can control these parameters using the **Transform**
menu in the source context menu. The transform parameters seem to be applied
in the following manner:

1. The image is scaled to the indicated **Size**. Initially the size will
be set to the natural size of the image, but this can be changed to make
the image larger or smaller. If the new size does not preserve the aspect
ration, the image will be distored. In OBS-Websocket the original image size
is **sourceWidth** and **sourceHeight** whereas **Size** is **width** and
**height**. The parameters **scaleX** and **scaleY** gives the scaling
ratio.
2. The image is cropped using the **Left**, **Right**, **Top**, and **Bottom**
parameters provided. Though the cropping is applied after scaling, the amount
to crop is in terms of the original image size.
3. If the **Bounding Box Type** is anything other than **No bounds**, the image
is scaled again to the size indicated in the **Bounding Box Size**.
    * **Stretch to bounds** -- The image is scaled to fill the entire bounding
box without regard to the aspect ratio
    * **Scale to inner bounds** -- image is sized to that it touches the bounding box at top and bottom or left and right, possibly leaving black bars in the other dimension
    * **Scale to outer bounds** -- no black bars, even if something has to be but off
    * **Scale to width of bounds** -- left and right edges or image touch left and right of bounding box, vertical discrepancy causes overflow or black bars
    * **Scale to height of bounds** -- top and bottom edgesof image touch top and bottom of bounding box, horizontal discrepancy causes overflow or black bars
    * **Maximum size only** -- shrink the image to fit completely within the bounds, but don't enlarge it to fill the bounds
4. If a bounding box was used and their is space left around the image, it is positioned as described in **Alignment in Bounding Box**.
5. The resulting image is placed at the indicated **Position** on the video canvas. The
**Position Alignment** parameter determines the anchor, the part of the image which is placed
at the indicated position. The default is to place the top-left corner
of the image at that position.
6. The image is rotated around the **Position** by the number of degrees
indicated in the **Rotation** parameter.
