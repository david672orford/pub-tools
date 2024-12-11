#! /bin/sh
set -eu

mkdir -p download
cd download
for url in \
		https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip \
		https://bootstrap.pypa.io/get-pip.py \
		https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/refs/heads/main/dlib-19.24.99-cp312-cp312-win_amd64.whl
	do
	filename=`basename $url`
	if [ ! -f $filename ]
		then
		wget $url
		fi
	done
cd ..

mkdir -p build/python
cd build/python
unzip ../../download/python-3.12.8-embed-amd64.zip
cat - <<HERE >sitecustomize.py
import sys
sys.path.insert(0, "")
sys.path.insert(1, "app.zip")
HERE
echo "import site" >>python312._pth

# Install dependencies
# Tested with Wine 10.0-rc1
wine python.exe ../../download/get-pip.py
wine python.exe -m pip install setuptools
if grep '^face-recognition==' ../../../../requirements.txt >/dev/null
	then
	wine python.exe -m pip install ../../download/dlib-19.24.99-cp312-cp312-win_amd64.whl
	fi
wine python.exe -m pip install -r ../../../../requirements.txt --no-warn-script-location

# Slim down
wine python.exe -m pip uninstall -y setuptools
rm -r Scripts Include
#find Lib/site-packages -name '*.dist-info' | xargs rm -r

find . -type f \
	| wixl-heat --prefix "./" \
		--component-group Python \
		--var var.PythonBuildDir \
		--directory-ref PYTHONINSTALLDIR \
		>../heat-python.wxs
