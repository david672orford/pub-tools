# Notes on Windows

These notes are releated to the onging work to port Pub Tools to Microsoft Windows.

## Unix Tools for Windows

These packages proved useful during developement.

* [Putty](https://www.putty.org/) -- SSH Client, useful for transfering files
* [Busybox](https://frippery.org/busybox/) -- Small versions of the standard Unix CLI tools
* [Git](https://git-scm.com/download/win) -- Includes Bash, Vim, etc. in addition to Git

## Python

### Python.org Installer

* [Python](https://www.python.org/downloads/windows/) -- Official packages

### Install Using Winget

    > winget install -e --id Python.Python.3.12
    > winget install -e --id=Python.Launcher

### Setting up Python Embedded

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

## Installing Dlib

Option 1, Compile from source:
    > winget install cmake
    > winget install --id Microsoft.VisualStudio.2022.Community --override "--wait --quiet --add ProductLang En-us --add Microsoft.VisualStudio.Workload.NativeDesktop --includeRecommended"
    > pip install dlib

Option 2, Download wheel from:
	https://github.com/z-mahmud22/Dlib_Windows_Python3.x
And install it:
    python -m pip install dlib-19.24.99-cp312-cp312-win_amd64.whl

## Building MSI Packages

* https://wiki.gnome.org/msitools/HowTo/CreateMSI
* https://www.firegiant.com/docs/wix/v3/tutorial/
* https://www.codeproject.com/Tips/105638/A-quick-introduction-Create-an-MSI-installer-with

## Running from a Zip

* https://stackoverflow.com/questions/52599007/python3-pkgutil-get-data-usage 
