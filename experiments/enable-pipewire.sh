#! /bin/sh
systemctl --user --now disable pulseaudio.service pulseaudio.socket
systemctl --user mask pulseaudio
systemctl --user unmask pipewire
systemctl --user --now enable pipewire pipewire-pulse wireplumber.service
LANG=C pactl info | grep '^Server Name'
