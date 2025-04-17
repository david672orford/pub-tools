# apt-get install icoutils
# apt-get install librsvg2-bin

RSVG_CONVERT=rsvg-convert
ICOTOOL=icotool

all:

build-icons:
	mkdir -p build/icons; \
	for icon in pub-tools khplayer epubs; \
		do \
		for size in 16 32 48 64; \
			do \
			$(RSVG_CONVERT) -w $${size} -h $${size} ../../icons/$${icon}.svg -o build/icons/$${icon}-$${size}x$${size}.png; \
			done; \
		$(ICOTOOL) -c -o build/icons/$$icon.ico build/icons/$${icon}-*x*.png; \
		rm build/icons/$${icon}-*x*.png; \
	done

# Download and configure Python and required packages
build/heat-python.wxs: build-python.sh ../../requirements.txt
	rm -rf build/python
	./build-python.sh

build/heat-ffmpeg.wxs: build-ffmpeg.sh
	rm -rf build/ffmpeg
	./build-ffmpeg.sh

# Combine the previously compiled Python runtime and application into an MSI installer
msi: build/heat-python.wxs build/heat-ffmpeg.wxs
	rm -rf build/app
	./build-app.sh
	wixl -vv \
		-o pub-tools.msi \
		-D AppBuildDir=build/app \
		-D PythonBuildDir=build/python \
		-D FFmpegBuildDir=build/ffmpeg \
		-D ProductVersion=0.9.1 \
		-D Win64=yes \
		--arch x64 \
		pub-tools.wxs build/heat-app.wxs build/heat-python.wxs build/heat-ffmpeg.wxs

# Copy the MSI installer to where our test Windows VM can see it.
install: msi
	cp pub-tools.msi ~/Downloads/WinShare/

# Remove the Python runtime, compiled application, and MSI installer
# If drive Z does not work, restart VirtIO-FS Service in the VM.
clean:
	rm -rf build
	rm -f pub-tools.msi
