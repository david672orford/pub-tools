#! /bin/sh
# Download and configure Python and required packages
set -eu

WINE=/opt/wine-stable/bin/wine

# Download Python, Get-PIP, and Dlib wheel
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

echo "Unpacking Python..."
mkdir -p build/python
cd build/python
unzip ../../download/python-3.12.8-embed-amd64.zip

echo "Configure sys.path..."
cat - <<HERE >sitecustomize.py
import sys
sys.path.insert(0, "")
sys.path.insert(-1, sys.path[-1] + ".zip")
HERE
echo "import site" >>python312._pth

# Install packages named in requirements.txt.
# Tested with Wine 10.0 (wine-stable in Ubuntu 24.04)
echo "Installing required Python packages..."
$WINE python.exe ../../download/get-pip.py
$WINE python.exe -m pip install setuptools
if grep '^face-recognition==' ../../../../requirements.txt >/dev/null
	then
	$WINE python.exe -m pip install ../../download/dlib-19.24.99-cp312-cp312-win_amd64.whl
	fi
$WINE python.exe -m pip install -r ../../../../requirements.txt --no-warn-script-location

# Slim down by removing unneeded scripts, C include files, tests, and metadata.
echo "Removing unnecessary package files..."
$WINE python.exe -m pip uninstall -y setuptools
rm -r Lib/site-packages/pip
rm -r Scripts Include
find Lib/site-packages -name '*.dist-info' | grep -v werkzeug | grep -v pymorphy3_dicts_ru | grep -v face_recognition | xargs rm -r
find Lib/site-packages -name __pycache__ | xargs rm -rf
find Lib/site-packages -name 'test*' -type d | xargs rm -rf
find Lib/site-packages -name '*.h' | xargs rm -f
find Lib/site-packages -name '*.pxi' | xargs rm -f
find Lib/site-packages -name 'include' | xargs rm -rf
rm -r Lib/site-packages/lxml/includes

# Compile Python source files to .pyc files and remove them.
echo "Compiling Python source code..."
python3 -m compileall -b Lib/site-packages
find Lib/site-packages -name '*.py' | xargs rm

# Move as many packages as we can into a zip file.
# File access in Windows is much slower than in Linux, so this
# speeds up startup.
echo "Packing packages into zipfile..."
cd Lib
mkdir tmp
cd site-packages
for i in \
		asttokens \
		blinker \
		bottle.pyc \
		cachelib \
		click \
		colorama \
		executing \
		flask \
		flask_babel \
		flask_caching \
		flask_sqlalchemy \
		icecream \
		idna \
		itsdangerous \
		jinja2 \
		mdurl \
		proxy_tools \
		pycparser \
		pygments \
		requests \
		rich \
		typing_extensions.pyc \
		urllib3 \
		websocket \
		werkzeug \
		werkzeug-3.1.3.dist-info \
		whoosh
	do
	mv $i ../tmp
	done
cd ../tmp
zip -r ../site-packages.zip .
cd ..
rm -r tmp
cd ..
if [ ! -d Lib ]
	then
	echo "Assertion failed: not at expected level"
	exit 1
	fi

# Create a list of files to include in the MSI.
echo "Creating manifest..."
find . -type f \
	| wixl-heat --prefix "./" \
		--component-group Python \
		--var var.PythonBuildDir \
		--directory-ref PYTHONINSTALLDIR \
		--win64 \
		>../heat-python.wxs

echo "Done."
