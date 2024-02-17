# Notes on Zoom

## Installation on Linux

* [Download for Linux](https://zoom.us/download?os=linux)
* [Release Notes for Linux](https://support.zoom.us/hc/en-us/articles/205759689)
* [Unoffical Apt Repository](https://www.matthewthom.as/mirrors/#zoom)

## Zoom meeting URLs

And ordinary meeting URL looks like this:

> <span>https://zoom.us/j/*meeting\_id*?pwd=*encrypted\_password*</span>

A meeting URL which takes the user to the web client looks like this:

> <span>https://zoom.us/wc/join/*meeting\_id*?pwd=*encrypted\_password*</span>

The algorithm for encrypting the password is not publicly known.

## Web Meeting SDK

The Web Meeting SDK can be used to create customized versions of the Zoom web client.

* [Zoom App Marketplace](https://marketplace.zoom.us/) - Sign in and choose Develop and then Build App
* [Zoom Meeting SDK for web](https://developers.zoom.us/docs/meeting-sdk/web/)
* [API Reference for "Client View"](https://marketplacefront.zoom.us/sdk/meeting/web/index.html)
* [API Reference for "Component View](https://marketplacefront.zoom.us/sdk/meeting/web/components/index.html)
* [API Declarations for Client View](https://github.com/zoom/meetingsdk-web/blob/master/index.d.ts)
* [API Declarations for Component View](https://github.com/zoom/meetingsdk-web/blob/master/embedded.d.ts)
* [Example of Component View Config](https://stackoverflow.com/questions/76831074/how-to-implement-multiple-spotlighting-using-the-zoom-web-sdk-in-component-view)

## Zoom Apps SDK

The Zoom Apps SDK can be used to create tools and plugins which can be embedded in the Zoom client.

* [Welcome to Zoom Apps SDK!](https://devforum.zoom.us/t/welcome-to-zoom-apps-sdk/70841)
* [Zoom Apps SDK](https://appssdk.zoom.us/classes/ZoomSdk.ZoomSdk.html)
* [Zoom Apps SDK on Github](https://github.com/zoom/appssdk)
* [Enable Developer Tools](https://developers.zoom.us/docs/zoom-apps/create/)
* [Question about Enabling Developer Tools](https://devforum.zoom.us/t/enabling-developer-tools-in-linux/97819)
* [Manipulating the UI](https://developers.zoom.us/docs/zoom-apps/guides/layers-manipulating-ui/)

## Native SDK

* [Linux Raw Recording Sample](https://github.com/zoom/meetingsdk-linux-raw-recording-sample)

