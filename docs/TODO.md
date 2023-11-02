# Pub-Tools TODO

## General

* Zoom in a browser source
* Load the .jwpub file with talk illustrations
* Load illustrations from .jwlplaylist files (and other zip files)
* Should we cache thumbnail images in the Videos, Books, and PeriodicalIssues objects?

## Scenes Tab (Long Term)

* Drag and drop into Scenes tab does not work in OBS browser dock
* Can we have video and image thumbnails in Scenes tab? Ideas:
  # We could save them to a thumbnails directory named for each scene. However this breaks if the scene is renamed.
  # Scenes are sources. It appears you can save arbitrary settings in source settings.
  # Perhaps we could use idea 1 as a cache for idea 2.
* Scenes tab should update its view when changes are made in OBS. Can we listen
  for events and send Turbo messages? (According to the OBS-Websocket documentation
  SceneListChanged does not fire when scenes are reordered. Propose a change?)

