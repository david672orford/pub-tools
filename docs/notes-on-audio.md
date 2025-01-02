# Notes on Audio for Linux

Here we have collected notes on the popular audio subsystems for Linux. These include
the ALSA audio drivers in the kernel and the PulseAudio sound server or its replacement
Pipewire.

## Audio in General

* [Audio API Quick Start Guide](https://habr.com/en/articles/663352/) -- Includes examples for playing and recording in PulseAudio
* [FFaudio](https://github.com/stsaz/ffaudio) -- Cross-platform audio library

## Pipewire

Pipewire is a new audio server which (as of late 2024) is steadily replacing
PulseAudio in popular Linux distributions.

* [Pipewire Project Site](https://www.pipewire.org/)
* [Pipewire Docs](https://pipewire.pages.freedesktop.org/pipewire/)
* [Pipewire Wiki](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/home)
* [Pipewire Guide](https://github.com/mikeroyal/PipeWire-Guide) -- Setting up Pipeware and compatible utilities
* [Pipewire on Debian](https://pipewire-debian.github.io/pipewire-debian/) -- Covers Wireplumber installation too, works on Ubuntu too
* [Pipewire Under the Hood](https://venam.nixers.net/blog/unix/2021/06/23/pipewire-under-the-hood.html) -- Decent overview from somebody frustrated by the poor documentation
* [Migrating from PulseAudio to Pipewire](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Migrate-PulseAudio)
* [Echo Cancel Module](https://docs.pipewire.org/page_module_echo_cancel.html)
* [Multiple ports simultaneously in PipeWire](https://denilson.sa.nom.br/blog/2023-11-10/pipewire-multiple-ports) -- How to prevent aggregation of multiple output ports into a single device with switchable output

### Wireplumber

Wireplumber is a Pipewire "session manager". This means that it makes decisions for Pipewire
on how audio should be routed between inputs, outputs, and applications.

* [Wireplumber Documentation](https://pipewire.pages.freedesktop.org/wireplumber/)
* [Wireplumber Docs](https://pipewire.pages.freedesktop.org/wireplumber/index.html)
* [Wireplumber in Arch Linux Wiki](https://wiki.archlinux.org/title/WirePlumber)
* [WirePlumber, the PipeWire session manager](https://www.collabora.com/news-and-blog/blog/2020/05/07/wireplumber-the-pipewire-session-manager/)

### Pipewire Programming Examples

* [A Custom PipeWire Node](https://bootlin.com/blog/a-custom-pipewire-node/) -- Simple audio file player

## PulseAudio

PulseAudio was the most popular Linux sound server before the introduction of
Pipewire. Because Pipewire implements important API's from its predecessor,
PulseAudio documentation and programming examples are still useful.

### PulseAudio Documentation

* [PulseAudio Documentation](https://www.freedesktop.org/software/pulseaudio/doxygen/index.html)
* [PulseAudio Wiki](https://www.freedesktop.org/wiki/Software/PulseAudio/)
* [Pulseaudio Modules](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/)
* [PulseAudio in Arch Linux Wiki](https://wiki.archlinux.org/title/PulseAudio)
* [PulseAudio Under the Hood](https://gavv.net/articles/pulseaudio-under-the-hood/)
* [Controlling PulseAudio from the Command Line](https://www.shallowsky.com/linux/pulseaudio-command-line.html)
* [Arch Wiki: PulseAudio: Microphone echo/noise cancellation](https://wiki.archlinux.org/title/PulseAudio#Microphone_echo/noise_cancellation)

### PulseAudio Programming Examples

* [Python Pulsectl](https://pypi.org/project/pulsectl/) -- Blocking high-level interface and bindings to Libpulse
* [PulseAudio client in pure JavaScript](https://github.com/mscdex/paclient)
* [Example of Playing and Recording Audio in Python](https://askubuntu.com/questions/1398632/how-can-i-fit-python-pyaudio-to-to-virtual-microphone-that-i-created)
* [Example of Sink Event Monitoring](https://gist.github.com/sound-logic/00cf28f83993a2f7199538d281f831ad)
* [Example of Volume Control](https://github.com/andornaut/pavolume/blob/master/pavolume.c)

## Virtual Audio Cables Recipies

* [OBS to Zoom Virtual Audio Cable](https://luke.hsiao.dev/blog/pipewire-virtual-microphone/) -- Links two null sinks in Pipewire
* [Virtual Audio Cable in Pulseaudio](https://unix.stackexchange.com/questions/576785/redirecting-pulseaudio-sink-to-a-virtual-source) -- See Christopher Donham's answer
* [Virtual Devices in Wireplumber](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Virtual-devices)
* [PipeWire how-to: uncomplicated loopbacks](https://sorrel.sh/blog/pipewire-how-to-static-loopbacks/)
* [How to use the command 'pw-loopback' (with examples)](https://commandmasters.com/commands/pw-loopback-linux/)

## Other Recipies

* [Rename Devices in Pipewire](https://unix.stackexchange.com/questions/648666/rename-devices-in-pipewire)
* [How to Disable Audio Devices in Pipewire / Wireplumber](https://gist.github.com/gtirloni/4384f4de6f4d3fda8446b04057ca5f9d)
* [Pulseaudio cracking/skipping sound glitches](https://community.solid-run.com/t/pulseaudio-crackling-skipping-sound-glitches/120)
* [Pipewire Equalizer](https://askubuntu.com/questions/1420560/can-anyone-recommend-a-good-audio-equalizer-for-ubuntu)
