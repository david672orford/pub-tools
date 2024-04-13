# Notes on OBS Studio

## OBS Studio Installation

* [OBS Main Site](https://obsproject.com/)
* [OBS Github Site](https://github.com/obsproject/obs-studio)
* [Building OBS Studio](https://github.com/obsproject/obs-studio/wiki/Building-OBS-Studio)
* [Build Instructions for Linux](https://github.com/obsproject/obs-studio/wiki/build-instructions-for-linux)
* [Building on Debian (from forum)](https://obsproject.com/forum/threads/debian-obs-studio-build-mini-howto.169680/)
* [Checking out Pull Requests](https://stackoverflow.com/questions/27567846/how-can-i-check-out-a-github-pull-request-with-git#30584951)

## Integration of OBS Studio with other Programs

Video and audio can be fed into and out of OBS using the virtual camera,
streaming protocols, and players embeded in browser sources.

* [How to Use OBS with Zoom](https://www.eigenmagic.com/2020/04/22/how-to-use-obs-studio-with-zoom/)
* [VDO.Ninja](https://docs.vdo.ninja/) -- Browser-based videoconferencing designed for integration with OBS
* [Send SRT Video from OBS to OBS without a Server](https://youtu.be/eDgZ-IqvCJc?si=jGq48syIcpUk4IIL) -- SRT is a streaming format which can connect programs

## OBS-Websocket

* [Github Site](https://github.com/obsproject/obs-websocket)
* [Protocol](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md)

## OBS Script Development

OBS embeds Lua and Python interpreters. Scripts written in these language can automate
tasks, be sources and sinks of video and audio, and perform filtering. Python scripts
do not generally run fast enough to process video, but Lua scripts do.

* [Python/Lua Scripting](https://docs.obsproject.com/scripting)
* [API Reference](https://docs.obsproject.com/reference-core-objects)
* [Getting Started With OBS Scripting](https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting)
* [Python Scripting Cheatsheet](https://github.com/upgradeQ/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API)
* [Tips and Tricks for Lua Scripts](https://obsproject.com/forum/threads/tips-and-tricks-for-lua-scripts.132256/) -- OBS Forum thread
* [Scripts Forum](https://obsproject.com/forum/resources/categories/scripts.5/)
* [Cheat Sheet for Creating Scenes and Scene Items Functions in Lua](https://github.com/Chriscodinglife/get-started-with-lua)

## Example Scripts

* [OBS-Libre-Macros](https://github.com/upgradeQ/obs-libre-macros) -- Interesting LUA examples
* [Scripting Tutorial Source Shake](https://obsproject.com/wiki/Scripting-Tutorial-Source-Shake)
* [Scripting Tutorial Halftone Filter](https://obsproject.com/wiki/Scripting-Tutorial-Halftone-Filter)
* [JW Timer](https://github.com/lucidokr/obs-jw-timer/) -- Countdown timer in text source
* [Lua Color Source](https://obsproject.com/forum/resources/lua-color-source.717/)
* [Pan Zoom Rotate Filter](https://obsproject.com/forum/resources/pan-zoom-rotate.1489/)
* [Projector Hotkeys](https://obsproject.com/forum/resources/projector-hotkeys.1197/)

## Plugin Development

* [Plugin API Docs](https://obsproject.com/docs/plugins.html)
* [OBS-V4L2Sink](https://github.com/CatxFish/obs-v4l2sink) -- Useful as example of an output plugin

## Interesting Plugins

* [Advanced Scene Switcher](https://github.com/WarmUpTill/SceneSwitcher)
* [Move Transition](https://github.com/exeldro/obs-move-transition)
* [Transitions Table](https://github.com/exeldro/obs-transition-table)
* [Source Dock](https://github.com/exeldro/obs-source-dock) -- Always show a particular source in UI
* [Downstream Keyer](https://github.com/exeldro/obs-downstream-keyer) -- Adds an overlay to all scenes
* [Shaderfilter](https://github.com/exeldro/obs-shaderfilter/) -- Write video filters in shader language
* [Background Removal](https://github.com/occ-ai/obs-backgroundremoval) -- Works, but not as well as Zoom's implementation
* [Virtual Background](https://github.com/kounoike/obs-virtualbg) -- Crashes
* [Pulseaudio App Capture](https://github.com/jbwong05/obs-pulseaudio-app-capture)
* [Some Plugins Under Development](https://obsproject.com/forum/threads/some-plugins-under-development.160557/)
* [OBS Studio Portable](https://github.com/wimpysworld/obs-studio-portable) -- OBS Studio built with 50 additional plugins

## Bugs and Feature Requests we are Following

* [Idea: Virtual Camera audio](https://ideas.obsproject.com/posts/1415/obs-virtual-camera-audio) -- Proposal to provide audio output
* [Idea: Additional 'Aux Send' / monitor channel, or 'Virtual Audio Output'](https://ideas.obsproject.com/posts/965/additional-aux-send-monitor-channel-or-virtual-audio-output)
* [PR: Sample Rate Conversion](https://github.com/obsproject/obs-studio/pull/6351) -- May be blocking implementation of audio output
* [PR: Virtual Camera Audio in Linux](https://github.com/obsproject/obs-studio/pull/8171) -- Uses ALSA loopback device
* [Bug: Under OBS 30.0.0 CreateScene reverses the order of sequentially added scenes](https://github.com/obsproject/obs-websocket/issues/1181)
* [Bug: Disappearing Docks](https://www.reddit.com/r/obs/comments/114lnoj/disappearing_docks_how_do_i_get_them_back/)
* [Bug: Crash in File Picker](https://github.com/obsproject/obs-browser/issues/384)
* Bug: DND of file into browser dock does nothing, but URL works
* [PR: linux-v4l2: Give camera up to 2 seconds to start](https://github.com/obsproject/obs-studio/pull/10335)
* [PR: linux-pulseaudio: Implement audio output](https://github.com/obsproject/obs-studio/pull/10495)
* [Bug: Browser Dock: Resize and DND signals become disconnected on Linux](https://github.com/obsproject/obs-browser/issues/437)
* [PR: Enable building with CEF 6261](https://github.com/obsproject/obs-browser/pull/434)

## Object Hierarcy

Each **Scene** has zero or more **Scene Items**. Each Scene Item has a **Source** to which it applies
a **Scene Item Transform**. A source is an **Input** or another Scene.

Scenes are identified by Name and by UUID. Scene Items are identified by Scene and ID. 
Scene Item ID's are a small integers. They are unique only within the scene.

Each Scene Item also has an **Index** which determines its place in the stacking order
within the Scene. The index starts with 0. Stacking orders ascend from background to
foreground. However, they descend in the Sources Dock.

## Coordinate Transformation of Scene Items

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

