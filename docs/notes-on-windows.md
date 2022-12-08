# Notes on Windows

## Unix Tools for Windows

* [Putty](https://www.putty.org/)
* [Busybox](https://frippery.org/busybox/)
* [Git](https://git-scm.com/download/win)
* [Python](https://www.python.org/downloads/windows/)

## Setting Up Python

Create directory:

    mkdir python-win64
    cd python-win64

Get embeddable Python from [Python Windows installers](https://www.python.org/downloads/windows/) and unpack it:

    unzip ~/Downloads/python-3.10.8-embed-amd64.zip

Install PIP:

    wget https://bootstrap.pypa.io/get-pip.py
    wine python.exe get-pip.py

Install dependency packages:

    wine python.exe -m pip install -r ../requirements.txt

Create sitecustomize.py 

    import sys
    sys.path.insert(0, '')

See [Setting up python's Windows embeddable distribution (properly)](https://dev.to/fpim/setting-up-python-s-windows-embeddable-distribution-properly-1081).

