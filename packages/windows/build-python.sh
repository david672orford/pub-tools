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
sys.path.insert(-1, sys.path[-1] + ".zip")
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
find Lib/site-packages -name '*.dist-info' | grep -v werkzeug | xargs rm -r
find Lib/site-packages -name __pycache__ | xargs rm -rf
find Lib/site-packages -name 'test*' -type d | xargs rm -r
rm -r Lib/site-packages/lxml/includes

# Compile
python3 -m compileall -b Lib/site-packages
find Lib/site-packages -name '*.py' | xargs rm

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
		pymorphy3 \
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
	echo "Assertion failed"
	exit 1
	fi

find . -type f \
	| wixl-heat --prefix "./" \
		--component-group Python \
		--var var.PythonBuildDir \
		--directory-ref PYTHONINSTALLDIR \
		>../heat-python.wxs
