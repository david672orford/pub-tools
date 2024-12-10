all:

build-python:
	./build-python.sh

msi:
	( cd ../.. && find start.py pub-tools flask venv_tool.py app obs-scripts -type f | grep -v __pycache__ ) \
		| wixl-heat --prefix "" \
			--component-group Pub-Tools \
			--var var.SourceDir \
			--directory-ref INSTALLDIR \
			>heat-pub-tools.wxs
	find python -type f \
		| wixl-heat --prefix "" \
		--component-group Python \
		--var var.PythonDir \
		--directory-ref INSTALLDIR \
		>heat-python.wxs
	wixl -vv \
		-o pub-tools.msi \
		-D SourceDir=../.. \
		-D PythonDir=. \
		pub-tools.wxs heat-pub-tools.wxs heat-python.wxs

install: msi
	cp pub-tools.msi ~/Downloads/WinShare/

clean:
	rm -f heat*.wxs
	rm -f pub-tools.msi
	rm -rf python
