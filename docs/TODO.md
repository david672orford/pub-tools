# Pub-Tools TODO

## General

* Load the jwpub file with talk illustrations
* Zoom in browser source
* Write better docs
* Create a cache cleaner

## Scenes Tab

* Drag and drop into Scenes tab does not work in OBS browser dock
* Can we have video and image thumbnails in Scenes tab?
* Scenes tab should response to changes. Can we listen for events and send
  Turbo messages? (According to the OBS-Websocket documentation
  SceneListChanged does not fire when scenes are reordered.)

## OBS Scripts

* Fix return-to-first-scene so it does not act if the user stopped the
  video by switching scenes
* Automatically stop videos before notice card
* Make sure virtual audio cable can start even if microphone and speakers
are not yet selected. It should leave off those connections.
* Add selection of the microphone and speakers to the script configuration screen.

