# Notes on Windows

A long-term goal is to get Pub-Tools running under Microsoft Windows. These
are our notes.

## Unix Tools for Windows

* [Putty](https://www.putty.org/) -- SSH Client
* [Busybox](https://frippery.org/busybox/) -- Small versions of the standard Unix CLI tools
* [Git](https://git-scm.com/download/win)
* [Python](https://www.python.org/downloads/windows/)

## Installing Dlib

Compile from source:
    > winget install cmake
    > winget install --id Microsoft.VisualStudio.2022.Community --override "--wait --quiet --add ProductLang En-us --add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended"
    > pip install dlib

Or download wheel from:
	https://github.com/z-mahmud22/Dlib_Windows_Python3.x
And install it:
    python -m pip install dlib-19.24.99-cp312-cp312-win_amd64.whl

## Setting up Python Embedded

We would like to bundle Pub-Tools with a Python runtime. The
Python Embedded distribution is a candidate. Here we install
and run it under Wine.

Create directory:

    mkdir python-win64
    cd python-win64

Get embeddable Python from [Python Windows installers](https://www.python.org/downloads/windows/)
and unpack it:

    unzip ~/Downloads/python-3.10.8-embed-amd64.zip

Install PIP:

    wget https://bootstrap.pypa.io/get-pip.py
    wine python.exe get-pip.py

Install dependency packages:

    wine python.exe -m pip install -r ../requirements.txt

Create sitecustomize.py

    import sys
    sys.path.insert(0, '')

See:

* [Setting up python's Windows embeddable distribution (properly)](https://dev.to/fpim/setting-up-python-s-windows-embeddable-distribution-properly-1081)
* [Unimplemented function KERNEL32.dll.CopyFile2](https://forum.winehq.org/viewtopic.php?t=39119)

## Building MSI Packages

* https://wiki.gnome.org/msitools/HowTo/CreateMSI
* https://www.firegiant.com/docs/wix/v3/tutorial/
* https://www.codeproject.com/Tips/105638/A-quick-introduction-Create-an-MSI-installer-with
