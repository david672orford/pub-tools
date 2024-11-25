# Enable enabled PulseAudio output

obs = obslua
output = nil
output_device = nil

function script_description()
	return "<h2>PulseAudio Output</h2><p>Start and stop audio output through the PulseAudio sound server</p>"
end

function script_defaults(settings)
	obs.obs_data_set_default_bool(settings, "enable", false)
	obs.obs_data_set_default_string(settings, "device", nil)
	obs.obs_data_set_default_string(settings, "description", "OBS Virtual Cable")
end

function script_properties()
    local props = obs.obs_properties_create()

	local select_widget = obs.obs_properties_add_list(props, "device", "Output Device", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_list_add_string(select_widget, "Default Sink", "default")
	-- obs.obs_property_list_add_string(select_widget, "OBS Virtual Cable", "obs-virt-cable")
	local handle = io.popen("pactl list short sinks")
	for line in handle:lines() do
		sink = string.match(line, "%d+%s+(%S+)")
		obs.obs_property_list_add_string(select_widget, "Sink " .. sink, sink)
	end

	obs.obs_properties_add_bool(props, "enable", "Enable")

	return props
end

function script_update(settings)
	enable = obs.obs_data_get_bool(settings, "enable")
	device = obs.obs_data_get_string(settings, "device")
	if enable then
		if output and device ~= output_device then
			stop_output()
		end
		if not output then
			print("Starting audio output" .. device)
			output = obs.obs_output_create("pulse_output", device, settings, nil)
			obs.obs_output_start(output)
		end
	else
		if output then
			stop_output()
		end
	end
end

function stop_output()
	print("Stopping audio output")
	if output then
		obs.obs_output_stop(output)
		obs.obs_output_release(output)
		output = nil
		output_device = nil
	else
		print("Already closed")
	end
end

function script_unload()
	stop_output()
end

