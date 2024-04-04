# Notes on Audio for Linux

Pipewire is a new audio server which is set to place PulseAudio in popular
Linux distributions.

## Pipewire and Wireplumber

* [Pipewire Guide](https://github.com/mikeroyal/PipeWire-Guide) -- Setting up Pipeware and compatible utilities
* [Pipewire on Debian](https://pipewire-debian.github.io/pipewire-debian/) -- Covers Wireplumber installation too, works on Ubuntu too
* [Pipewire Wiki](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/home)
* [Wireplumber Documentation](https://pipewire.pages.freedesktop.org/wireplumber/)
* [Pipewire Under the Hood](https://venam.nixers.net/blog/unix/2021/06/23/pipewire-under-the-hood.html) -- Decent overview from somebody frustrated by the poor documentation
* [Migrate PulseAudio](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Migrate-PulseAudio)
* [Pipewire Docs](https://pipewire.pages.freedesktop.org/pipewire/)
* [Wireplumber Docs](https://pipewire.pages.freedesktop.org/wireplumber/index.html)
* [A Custom PipeWire Node](https://bootlin.com/blog/a-custom-pipewire-node/) -- A virtual audio source from an audio file

## PulseAudio

Pipewire has partial backwards compatibility with PulseAudio. This includes support for
the API for playing and recording sound and the **pactl** command.

* [PulseAudio Documentation](https://www.freedesktop.org/software/pulseaudio/doxygen/index.html)
* [PulseAudio Wiki](https://www.freedesktop.org/wiki/Software/PulseAudio/)
* [PulseAudio in Arch Linux Wiki](https://wiki.archlinux.org/title/PulseAudio)
* [PulseAudio Under the Hood](https://gavv.net/articles/pulseaudio-under-the-hood/)
* [Python Pulsectl](https://pypi.org/project/pulsectl/) -- Blocking high-level interface and bindings to Libpulse
* [PulseAudio client in pure JavaScript](https://github.com/mscdex/paclient)
* [Example of Playing and Recording Audio in Python](https://askubuntu.com/questions/1398632/how-can-i-fit-python-pyaudio-to-to-virtual-microphone-that-i-created)
* [Audio API Quick Start Guide](https://habr.com/en/articles/663352/) -- Includes examples for playing and recording in PulseAudio

## Virtual Audio Cables

* [Virtual Devices in Wireplumber](https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Virtual-devices)
* [Pulseaudio Modules](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/) -- Some of this carries over to Pipewire
* [Virtual Audio Cable in Pulseaudio](https://unix.stackexchange.com/questions/576785/redirecting-pulseaudio-sink-to-a-virtual-source) -- See Christopher Donham's answer
* [OBS to Zoom Virtual Audio Cable](https://luke.hsiao.dev/blog/pipewire-virtual-microphone/) -- This one successfully connects the null sync and the remapper

## Utilities Compatible with Pipewire

* [Helvum GUI Patchbay for Pipewire](https://gitlab.freedesktop.org/pipewire/helvum) -- Very basic, widgets overlap on HiDPI displays, user repeats drawing of a link to delete it
* [QPWgraph](https://gitlab.freedesktop.org/rncbc/qpwgraph) -- GUI interface to Pipewire's graph, clutters with MIDI and video, one box for each OBS audio source
* [QjackCtl](https://qjackctl.sourceforge.io/) -- GUI for the JACK audio server, compatible with Pipewire, clutters with MIDI, one box for all OBS sources
* [Catia](https://kx.studio/Applications:Catia) -- Another GUI for JACK which can be used with Pipewire, clutters with MIDI, one box for all OBS sources

## Compatible Audio Filters

* [NoiseTorch](https://github.com/noisetorch/NoiseTorch) -- Creates a filtered virtual microphone

## Recipies

* [Rename Devices in Pipewire](https://unix.stackexchange.com/questions/648666/rename-devices-in-pipewire)
* [How to Disable Audio Devices in Pipewire / Wireplumber](https://gist.github.com/gtirloni/4384f4de6f4d3fda8446b04057ca5f9d)
* [Pulseaudio cracking/skipping sound glitches](https://community.solid-run.com/t/pulseaudio-crackling-skipping-sound-glitches/120)

