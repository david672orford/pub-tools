all:

build-python:
	./build-python.sh

build-app:
	./build-app.sh

msi:
	wixl -vv \
		-o pub-tools.msi \
		-D AppBuildDir=build/app \
		-D PythonBuildDir=build/python \
		pub-tools.wxs build/heat-app.wxs build/heat-python.wxs

install: msi
	cp pub-tools.msi ~/Downloads/WinShare/

clean:
	rm -rf build
	rm -f pub-tools.msi
