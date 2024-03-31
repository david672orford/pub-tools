#! /bin/bash

# Load video loopback device at boot, make it /dev/video10 with
# the name "OBS Virtual Camera".
echo v4l2loopback \
	| sudo tee /etc/modules-load.d/v4l2loopback.conf
echo 'options v4l2loopback video\_nr=10 card_label="OBS Virtual Camera"' \
	| sudo tee /etc/modprobe.d/v4l2loopback.conf

## Load an audio loopback device
#echo snd_aloop \
#	| sudo tee /etc/modules-load.d/alsa-loopback.conf

## Disable setup of the loopback device in Wireplumber
#mkdir -p ~/.config/wireplumber/main.lua.d
#cat - >~/.config/wireplumber/main.lua.d/51-no-loopback.lua <<HERE
#table.insert(alsa_monitor.rules, {
#	matches = {
#		{
#			-- Wireplugger doesn't seem to get set up right, we get no sound
#			{ "device.name", "equals", "alsa_card.platform-snd_aloop.0" },
#		},
#	},
#    apply_properties = {
#		["device.disabled"] = true,
#	},
#})
#HERE

## Configure the audio loopback device in Pipewire
#mkdir -p ~/.config/pipewire/pipewire.conf.d
#cd ~/.config/pipewire
#if [ ! -f pipewire.conf ]
#	then
#	ln -s /usr/share/pipewire/pipewire.conf .
#cat - >>pipewire.conf.d/50-alsa-loopback.conf <<HERE
#context.objects = [
#    { factory = adapter
#        args = {
#            factory.name           = api.alsa.pcm.source
#            node.name              = "OBS Virtual Microphone"
#            node.description       = "OBS Virtual Microphone"
#            media.class            = "Audio/Source"
#            api.alsa.path          = "hw:Loopback,1,0"
#            api.alsa.period-size   = 1024
#            api.alsa.headroom      = 0
#            api.alsa.disable-mmap  = false
#            api.alsa.disable-batch = false
#            audio.format           = "S16LE"
#            audio.rate             = 48000
#            audio.channels         = 2
#            audio.position         = "FL,FR"
#        }
#    }
#	]
#HERE

# Start it all
sudo modprobe v4l2loopback
#sudo modprobe snd_aloop
#systemctl --user restart pipewire
#systemctl --user restart wireplumber

