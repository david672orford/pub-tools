#! /bin/sh
# Download and configure FFmpeg
set -eu

mkdir -p download
cd download

url="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.7z"
filename=`basename $url`
if [ ! -f $filename ]
	then
	wget $url
	fi
cd ..

mkdir -p build/ffmpeg
cd build/ffmpeg
7z e ../../download/ffmpeg-release-essentials.7z -obin ffmpeg.exe -r

# Create a list of files to include in the MSI.
echo "Creating manifest..."
find . -type f \
		| wixl-heat --prefix "./" \
			--component-group FFmpeg \
			--var var.FFmpegBuildDir \
			--directory-ref FFMPEGINSTALLDIR \
			--win64 \
			>../heat-ffmpeg.wxs

echo "Done."
