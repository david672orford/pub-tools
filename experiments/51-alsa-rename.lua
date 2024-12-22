-- ~/.config/wireplumber/main.lua.d/51-alsa-overrides.lua
-- Rename Audio Devices
--
-- This is for Wireplumber version 0.4.17. In version 0.5 the format will
-- change from Lua to a dialect of JSON.
--
-- See /usr/share/wireplumber/main.lua.d/50-alsa-config.lua for context.
--
-- To list devices and nodes:
--  pw-cli ls Device
--  pw-cli ls Node
--  pw-cli ls Port
--
-- To test first stop Wireplumber:
--   $ systemctl --user stop wireplumber
-- Then run it in the foreground to try your configuration:
--   $ WIREPLUMBER_DEBUG=2 wireplumber
-- Once you have everything the way you want it, restart the Wireplumber:
--   $ systemctl --user start wireplumber

-- Rename USB Microphone
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "device.name", "equals", "alsa_card.usb-Clip-on_USB_microphone_UM02-00" },
		},
	},
    apply_properties = {
		["device.nick"] = "USB Microphone",
		["device.description"] = "USB Microphone"
	},
})

-- Rename Built-in Audio Card
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "device.name", "equals", "alsa_card.pci-0000_08_00.6" },
		},
	},
    apply_properties = {
		["device.nick"] = "Built-in Audio",
		["device.description"] = "Built-in Audio Controller"
	},
})

-- Rename Speakers
table.insert(alsa_monitor.rules, {
	matches = {
		{
			{ "node.name", "equals", "alsa_output.pci-0000_08_00.6.analog-stereo" },
		},
	},
    apply_properties = {
		["node.nick"] = "Line Out",
		["node.description"] = "Stereo Analog Line Out"
	},
})

