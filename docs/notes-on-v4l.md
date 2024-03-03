# Notes on Video for Linux

## List Devices:

    $ v4l2-ctl --list-devices

## Adjust Brightness, Contrast, etc.

    $ apt install qv4l2
    $ qv4l2

## Stable Device Nodes for Cameras

    $ udevadm info -a /dev/video1
    $ sudo vi /etc/udev/rules.d/99-local.rules
    $ sudo udevadm control --reload-rules && sudo udevadm trigger

Sample rule:

    SUBSYSTEM=="video4linux", ATTR{name}=="CREALITY CAM: HD 4MP WEBCAM", SYMLINK+="video-webcam"

As an alternative, you can just use the symbolic links created by default in /dev/v4l/by-id/ or /dev/v4l/by-path/.

## Loopback Device

    $ sudo modprobe v4l2loopback video\_nr=10 card_label="OBS Virtual Camera"

## References

* [The Video for Linux API](https://www.kernel.org/doc/html/v4.8/media/uapi/v4l/v4l2.html)
* [Assign v4l2 device a static name](https://docs.formant.io/docs/assign-v4l2-device-a-static-name)

