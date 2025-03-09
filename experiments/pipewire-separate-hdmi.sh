#! /bin/bash

CONFDIR=~/.config/alsa-card-profile/mixer/profile-sets

if [ ! -d $CONFDIR ]
	then
	mkdir -p $CONFDIR
	fi

ln -sf /usr/share/alsa-card-profile/mixer/profile-sets/default.conf $CONFDIR

cat - >$CONFDIR/9999-custom.conf HERE
# By default Pipewire combines all of the HDMI audio outputs into a
# single appearent devices with switchable outputs. This fragment
# splits three HDMI outputs into separate devices.
[Profile output:hdmi-stereo+output:hdmi-stereo-extra1+output:hdmi-stereo-extra2+input:analog-stereo]
description = Three HDMI Ports
output-mappings = hdmi-stereo hdmi-stereo-extra1 hdmi-stereo-extra2
HERE

systemctl --user restart pipewire
