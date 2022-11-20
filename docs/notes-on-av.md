# Audio-Visual Technology Notes

## OBS

* [Advanced Scene Switcher](https://github.com/WarmUpTill/SceneSwitcher)
* [Pulseaudio App Capture](https://github.com/jbwong05/obs-pulseaudio-app-capture)
* [How to Use OBS with Zoom](https://www.eigenmagic.com/2020/04/22/how-to-use-obs-studio-with-zoom/)
* [VDO.Ninja](https://docs.vdo.ninja/)
* [Pulseaudio audio-monitoring list sinks](https://github.com/obsproject/obs-studio/pull/4226)

## Pipewire Audio Server for Linux

* [Pipewire Guide](https://github.com/mikeroyal/PipeWire-Guide) -- Setting up Pipeware and compatible utilities
* [Pipewire on Debian](https://pipewire-debian.github.io/pipewire-debian/)
* [Helvum GUI Patchbay for Pipewire](https://gitlab.freedesktop.org/pipewire/helvum)
* [QPWgraph](https://gitlab.freedesktop.org/rncbc/qpwgraph) -- GUI interface to Pipewire's graph, clutters with MIDI and video, one box for each OBS audio source
* [QjackCtl](https://qjackctl.sourceforge.io/) -- GUI for the JACK audio server, compatibel with Pipewire, clutters with MIDI, one box for all OBS sources
* [Catia](https://kx.studio/Applications:Catia) -- Another GUI for JACK which can be used with Pipewire, clutters with MIDI, one box for all OBS sources
* [Pulseaudio Modules](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/Modules/) -- Some of this carries over to Pipewire
* [Virtual Audio Cable in Pulseaudio](https://unix.stackexchange.com/questions/576785/redirecting-pulseaudio-sink-to-a-virtual-source) -- See Christopher Donham's answer
* [OBS to Zoom Virtual Audio Cable](https://luke.hsiao.dev/blog/pipewire-virtual-microphone/) -- This one successfully connects the null sync and the remapper

## FFmpeg

* https://pypi.org/project/python-ffmpeg/
* https://superuser.com/questions/326629/how-can-i-make-ffmpeg-be-quieter-less-verbose

Black detection using FFmpeg:

    $ ffmpeg -i clip.mp4 -vf blackdetect=d=0.1:pix_th=.1 -f rawvideo -y /dev/null

