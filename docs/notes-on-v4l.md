# Notes on Video for Linux

## List Cameras

Using Video4Linux 2 utilities:

    $ v4l2-ctl --list-devices

See app/subapps/khplayer/utils/cameras.py for how to do this using the /sys filesystem.

## Adjust Brightness, Contrast, etc.

    $ apt install qv4l2
    $ qv4l2

## Udev Rules for Cameras

Find the attributes of the device:

    $ udevadm info -a /dev/video0

Write a Udev rule:

    $ sudo vi /etc/udev/rules.d/99-local.rules

Test the rule:

    $ udevadm test $(udevadm info -q path -n /dev/video0)

Reload the rules:

    $ sudo udevadm control --reload-rules && sudo udevadm trigger

## Stable Symlink

Add a Udev rule like this:

    SUBSYSTEM=="video4linux", ATTR{name}=="CREALITY CAM: HD 4MP WEBCAM", SYMLINK+="video-webcam"

As an alternative, you can just use the symbolic links created by default in /dev/v4l/by-id/ or /dev/v4l/by-path/.

## Overriding Camera Names

You can create a Udev rule like this:

    SUBSYSTEMS=="usb", ENV{ID_VENDOR_ID}=="32e4", ENV{ID_MODEL_ID}=="9230", ENV{ID_V4L_PRODUCT}="ELP 2.0 MP Camera"

However, this does not change the name displayed by **v4l2-ctl --list-devices** or seen by OBS.

## Loopback Device

    $ sudo modprobe v4l2loopback video\_nr=10 card_label="OBS Virtual Camera"

## References

* [The Video for Linux API](https://www.kernel.org/doc/html/v4.8/media/uapi/v4l/v4l2.html)
* [Assign v4l2 device a static name](https://docs.formant.io/docs/assign-v4l2-device-a-static-name)
