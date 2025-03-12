#! /bin/sh
# Make a compiled copy of the application including only necessary files
set -eu

mkdir -p build/app
cd build/app
ROOT=../../../..

# Copy the parts of the app which we need
cp -Rv $ROOT/start.py $ROOT/flask $ROOT/pub-tools $ROOT/venv_tool.py $ROOT/app $ROOT/obs-scripts .
find . -name __pycache__ | xargs rm -r
find . -name .ropeproject | xargs rmdir
find . -name '*.md' | xargs rm

# Compile .py module files to .pyc and remove the .py files
python3 -m compileall -b app obs-scripts/.libs venv_tool.py
find app -name '*.py' | xargs rm

## Move the .pyc files into a zip archive
#zip -r app.zip app obs-scripts/.libs venv_tool.py
#find app obs-scripts/.libs venv_tool.pyc -name '*.pyc' | xargs rm

find . -type f \
	| wixl-heat --prefix "./" \
		--component-group Pub-Tools \
		--var var.AppBuildDir \
		--directory-ref INSTALLDIR \
		>../heat-app.wxs
