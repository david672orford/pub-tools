# Pub-Tools TODO

## General

* Write better docs (underway)
* Zoom in a browser source
* Load the jwpub file with talk illustrations
* Should we cache thumbnail images in the Videos, Books, and PeriodicalIssues objects

## OBS Scripts (Short Term)

* Fix return-to-first-scene so it does not act if the user stopped the
  video by switching scenes
* Automatically stop videos before notice card
* Make sure virtual audio cable can start even if microphone and speakers
are not yet selected. It should leave off those connections.
* Add selection of the microphone and speakers to the script configuration screen.

## Scenes Tab (Long Term)

* Drag and drop into Scenes tab does not work in OBS browser dock
* Can we have video and image thumbnails in Scenes tab? Perhaps by saving them
  to a thumbnails directory? The problem is that in order to find them there
  we would have to enumerate the sources of each scene.
* Scenes tab should update its view when changes are made in OBS. Can we listen
  for events and send Turbo messages? (According to the OBS-Websocket documentation
  SceneListChanged does not fire when scenes are reordered.)

