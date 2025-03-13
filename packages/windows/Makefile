# apt-get install icoutils
# apt-get install librsvg2-bin

RSVG_CONVERT=rsvg-convert
ICOTOOL=icotool

all:

# Download and configure Python and required packages
build-python:
	rm -rf build/python
	./build-python.sh

# Make a compiled copy of the application including only necessary files
build-app:
	rm -rf build/app
	./build-app.sh

# Combine the previously compiled Python runtime and application into an MSI installer
msi:
	wixl -vv \
		-o pub-tools.msi \
		-D AppBuildDir=build/app \
		-D PythonBuildDir=build/python \
		pub-tools.wxs build/heat-app.wxs build/heat-python.wxs

build-icons:
	mkdir -p build/icons; \
	for icon in pub-tools khplayer epub; \
		do \
		for size in 16 32 48 64; \
			do \
			$(RSVG_CONVERT) -w $${size} -h $${size} ../../icons/$${icon}.svg -o build/icons/$${icon}-$${size}x$${size}.png; \
			done; \
		$(ICOTOOL) -c -o build/icons/$$icon.ico build/icons/$${icon}-*x*.png; \
		rm build/icons/$${icon}-*x*.png; \
	done

# Copy the MSI installer to where our test Windows VM can see it.
install: msi
	cp pub-tools.msi ~/Downloads/WinShare/

# Remove the Python runtime, compiled application, and MSI installer
# If drive Z does not work, restart VirtIO-FS Service in the VM.
clean:
	rm -rf build
	rm -f pub-tools.msi
