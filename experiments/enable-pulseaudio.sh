#! /bin/sh
systemctl --user --now disable pipewire pipewire-pulse wireplumber.service
systemctl --user mask pipewire
systemctl --user unmask pulseaudio
systemctl --user --now enable pulseaudio.service pulseaudio.socket
LANG=C pactl info | grep '^Server Name'
