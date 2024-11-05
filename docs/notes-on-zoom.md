# Notes on Zoom

## Installation

* [Download for Linux](https://zoom.us/download?os=linux)
* [Other Installers](https://support.zoom.com/hc/ru/article?id=zm_kb&sysparm_article=KB0060410)
* [Release Notes](https://support.zoom.com/hc/ru/article?id=zm_kb&sysparm_article=KB0061222)
* [Unoffical Apt Repository](https://www.matthewthom.as/mirrors/#zoom)

## Suppressing Non-Standard UI Behaviors

Edit ~/.config/zoomus.conf and make sure you have the following settings:

    showSystemTitlebar=true
    enableMiniWindow=false

The first change restores the window manager title bars which were suppressed in Zoom 6.
The second change prevents Zoom from turning into a weird little always-on-top picture
of the current speaker whenever you switch virtual desktops. 

## Zoom meeting URLs

And ordinary meeting URL looks like this:

> https<span>://</span>zoom.us/j/*meeting\_id*?pwd=*encrypted\_password*

A meeting URL which takes the user to the web client looks like this:

> https<span>://</span>zoom.us/wc/join/*meeting\_id*?pwd=*encrypted\_password*

The algorithm for encrypting the password is not publicly known.

## Capturing Video

* If dual-monitor mode is enabled, the current speaker will be displayed in a second window which can be easily captured in OBS.
* Could use the Web Meeting SDK in an OBS browser source. Quality would likely be low.
* Could use the Zoom Apps SDK to enable immersive mode and place participant video at stable locations, but Zoom Apps do not actually work yet on Linux.
* Could use the Linux Native SDK, but this would require a lot of work to integrate it with OBS.

## Web Meeting SDK

The Web Meeting SDK can be used to create customized versions of the Zoom web client.

* [Zoom Meeting SDK for web](https://developers.zoom.us/docs/meeting-sdk/web/)
* [API Reference for "Client View"](https://marketplacefront.zoom.us/sdk/meeting/web/index.html)
* [API Reference for "Component View](https://marketplacefront.zoom.us/sdk/meeting/web/components/index.html)
* [API Declarations for Client View](https://github.com/zoom/meetingsdk-web/blob/master/index.d.ts)
* [API Declarations for Component View](https://github.com/zoom/meetingsdk-web/blob/master/embedded.d.ts)
* [Example of Component View Config](https://stackoverflow.com/questions/76831074/how-to-implement-multiple-spotlighting-using-the-zoom-web-sdk-in-component-view)

## Zoom Apps SDK

The Zoom Apps SDK can be used to plugins which can be embedded in the Zoom client. These
plugins are written in HTML and Javascript.

* [Zoom App Marketplace](https://marketplace.zoom.us/) - Sign in and choose Develop and then Build App
* [Welcome to Zoom Apps SDK!](https://devforum.zoom.us/t/welcome-to-zoom-apps-sdk/70841)
* [Zoom Apps SDK](https://appssdk.zoom.us/classes/ZoomSdk.ZoomSdk.html)
* [Zoom Apps SDK on Github](https://github.com/zoom/appssdk)
* [Enable Developer Tools](https://developers.zoom.us/docs/zoom-apps/create/)
* [Question about Enabling Developer Tools](https://devforum.zoom.us/t/enabling-developer-tools-in-linux/97819)
* [Manipulating the UI](https://developers.zoom.us/docs/zoom-apps/guides/layers-manipulating-ui/)
* [Custom Layout Example](https://github.com/zoom/zoomapps-customlayout-js)

## Native SDK

* [Zoom Meeting SDK for Linux](https://developers.zoom.us/docs/meeting-sdk/linux/)
* [Linux Raw Recording Sample](https://github.com/zoom/meetingsdk-linux-raw-recording-sample)
* [Linux Headless Sample](https://github.com/zoom/meetingsdk-headless-linux-sample)
* [Meeting API Reference](https://marketplacefront.zoom.us/sdk/meeting/linux/index.html)
