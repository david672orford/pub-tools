#! /bin/sh
set -eu

mkdir -p build/app
cd build/app
ROOT=../../../..

cp -Rv $ROOT/flask $ROOT/pub-tools $ROOT/venv_tool.py $ROOT/app $ROOT/obs-scripts .
python -m compileall -b .
find app -name '*.py' | xargs rm

find . -type f \
	| wixl-heat --prefix "./" \
		--component-group Pub-Tools \
		--var var.AppBuildDir \
		--directory-ref INSTALLDIR \
		>../heat-app.wxs
