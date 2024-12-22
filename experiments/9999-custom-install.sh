#! /bin/bash
CONFDIR=~/.config/alsa-card-profile/mixer/profile-sets
if [ ! -d $CONFDIR ]
	then
	mkdir -p $CONFDIR
	fi
ln -sf /usr/share/alsa-card-profile/mixer/profile-sets/default.conf $CONFDIR
cp 9999-custom.conf $CONFDIR
