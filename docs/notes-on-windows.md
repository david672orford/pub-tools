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

* [WiX Toolset v3 Manual](https://www.firegiant.com/wix3/)
* MSI Tools (WiX compatible tools from the GNOME project)
  * [MSI Tools](https://wiki.gnome.org/msitools/)
  * [MSI Tools on Github](https://github.com/GNOME/msitools)
  * [Beginner's guide to MSI creation](https://wiki.gnome.org/msitools/HowTo/CreateMSI)
* [WiX for the impatient](http://www.p-nand-q.com/programming/windows/wix/) -- Three blog articles
* [A quick introduction: Create an MSI installer with WiX](https://www.codeproject.com/Tips/105638/A-quick-introduction-Create-an-MSI-installer-with) -- Good example with Start Menu
* [Real-World Example: WiX/MSI Application Installer](https://helgeklein.com/blog/real-world-example-wix-msi-application-installer/)

## Running from a Zip

* https://stackoverflow.com/questions/52599007/python3-pkgutil-get-data-usage 
* https://realpython.com/python-zip-import/
* https://docs.python.org/3/library/zipimport.html

## Powershell

* https://serverfault.com/questions/877548/how-to-download-an-archive-and-extract-it-without-saving-the-archive-to-disk-usi

## Porting from Linux to Windows

* File names are case-sensitive in Linux, but case-insensitive in Windows
* On Unix the path separator is /, on Windows it is either / or \
* Colons are not allowed in file names on Windows (except as part of the drive letter)
* Working with large numbers of small files (such as Python modules) is much more expensive on Windows
* On Linux ffmpeg is likely to be installed and in the path, but not in Windows
* On Linux it is highly likely that Python 3 will be installed, but not in Windows
* Linux follows the Desktop Entry Specification for start menu items, Windows uses its own LNK format
* On Linux menu icons may be in PNG or SVG format. In Windows they must be in ICO format.
* On Linux 3rd-party programs are installed in /opt. On Windows they are installed in c:\Program Files.
* On Linux per-user application data is stored in $HOME/.config and $HOME/.local while on Windows
  it is stored in $HOME/AppData.
* On Linux and Windows use diferent locale name formats. Examples from locale.getlocale():
  * Linux: ('en_US', 'UTF-8')
  * Windows: ('English_United States', '1252')
