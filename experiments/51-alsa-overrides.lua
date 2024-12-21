-- ~/.config/wireplumber/main.lua.d/55-alsa-overrides.lua
-- Audio Devices Setup
--
-- This is for Wireplumber version 0.4.17. In version 0.5 the format will
-- change from Lua to a dialect of JSON.
--
-- See <https://unix.stackexchange.com/questions/648666/rename-devices-in-pipewire> for discussion.
-- See /usr/share/wireplumber/main.lua.d/50-alsa-config.lua for context.
--
-- To list devices and nodes:
--  pw-cli ls Device
--  pw-cli ls Node
--  pw-cli ls Port
--
-- Find the device.name or node.name of the thing you want to disable and 
-- make a rule for it using a model below.
--
-- To test:
--  systemctl --user stop wireplumber
--  wireplumber
--
-- Restart:
--   systemctl --user start wireplumber

-- Disable unusable and unneeded devices
table.insert(alsa_monitor.rules, {
	matches = {
		{
			-- Despite what it claims, USB video camera does not actually have a microphone
			{ "device.name", "equals", "alsa_card.usb-Creality_3D_Technology_CREALITY_CAM_20220121-02" },
		},
		{
			-- The monitor (screen) has no speakers, so HDMI audio output is useless
			{ "device.name", "equals", "alsa_card.pci-0000_08_00.1" },
		},
	},
    apply_properties = {
		["device.disabled"] = true,
	},
})

-- Disable unusable parts of devices
table.insert(alsa_monitor.rules, {
	matches = {
		{
			-- We never use the analog line in
			{ "node.name", "equals", "alsa_input.pci-0000_08_00.6.analog-stereo" },
		},
	},
    apply_properties = {
		["node.disabled"] = true,
	},
})

-- Rename Microphone
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "device.name", "equals", "alsa_card.usb-Solid_State_System_Co._Ltd._LCS_USB_Audio_000000000000-00" },
		},
	},
    apply_properties = {
		["device.nick"] = "USB Microphone",
		["device.description"] = "USB Microphone"
	},
})

-- Rename Speakers
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "device.name", "equals", "alsa_card.pci-0000_08_00.6" },
		},
	},
    apply_properties = {
		["device.nick"] = "HD Audio",
		["device.description"] = "HD Audio Controller"
	},
})
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "node.name", "equals", "alsa_output.pci-0000_08_00.6.analog-stereo" },
		},
	},
    apply_properties = {
		["node.nick"] = "Speakers",
		["node.description"] = "HD Audio Stereo Analog Line Out"
	},
})

