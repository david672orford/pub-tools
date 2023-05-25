# Notes on Video for Linux

## List Devices:

  $ v4l2-ctl --list-devices

## Stable Device Nodes for Cameras

  $ udevadm info -a /dev/video1
  $ sudo vi /etc/udev/rules.d/99-local.rules
  $ sudo udevadm control --reload-rules && sudo udevadm trigger

Sample rule:

  SUBSYSTEM=="video4linux", ATTR{name}=="CREALITY CAM: HD 4MP WEBCAM", SYMLINK+="video-webcam"

As an alternative, you can just use the symbolic links created by default in /dev/v4l/by-id/ or /dev/v4l/by-path/.

## References

* [Assign v4l2 device a static name](https://docs.formant.io/docs/assign-v4l2-device-a-static-name)

