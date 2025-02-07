# Set to a random value
SECRET_KEY = "__secret_key_here__"

# Select theme. Default is "basic-light" or "basic-dark" when running under OBS in dark mode.
#THEME="basic-light"
#THEME="basic-dark"
#THEME="colorful"

# Pub-Tools has several applications which can be enabled individually
#ENABLED_SUBAPPS = [
#	"khplayer",
#	"toolbox",
#	"epubs",
#	"admin",
#	]

# Language for user interface (defaults to the system locale)
#UI_LANGUAGE="ru"

# Language for loading publications, videos (defaults to UI_LANGUAGE)
#PUB_LANGUAGE="ru"

# Uncomment to enable subtitles in videoes, where available (defaults to disabled)
#SUB_LANGUAGE="en"

# Set to "240p", "360p", "480p", or "720p" (defaults to "720p")
#VIDEO_RESOLUTION="480p"

# Size of text in browser dock may be off
#OBS_BROWSER_DOCK_SCALE = 1.0

# Override OBS-Websocket configuration
# Default: read from OBS configuration file
#OBS_WEBSOCKET = {
#	"hostname": "localhost",
#	"port": 4455,
#	"password": "__change_me__",
#	}

# Patchbay mode:
# False - Disable
# True - Enable
# "virtual-cable" - Enable and enable virtual cable controls
#PATCHBAY = "virtual-cable"

# Assign OBS source names to V4L2 devices
# To see the device names:
# $ v4l2-ctl --list-devices
#CAMERA_NAME_OVERRIDES = {
#	"CREALITY CAM: HD 4MP WEBCAM": "Good Webcam",
#	"HD USB Camera: HD USB Camera": "ELP 2.0 MP Webcam",
#	}

# Sources using VDO.Ninja
#VIDEO_REMOTES = {
#	"Main Hall": {
#		"view": "my-channel-123",
#	},
#	"Other Hall": {
#		"view": "my-channel-124",
#	},
#}

# "Update Stream URLs" button configuration
# Format: CSV
# Column: URL
#JWSTREAM_UPDATES = "URL Here"
