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
end

function script_properties()
    local props = obs.obs_properties_create()

	local select_widget = obs.obs_properties_add_list(props, "device", "Output Device", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
	obs.obs_property_list_add_string(select_widget, "Default", nil)
	obs.obs_property_list_add_string(select_widget, "OBS Virtual Microphone", "OBS Virtual Microphone")
	local handle = io.popen("pactl list short sinks")
	for line in handle:lines() do
		sink = string.match(line, "%d+%s+(%S+)")
		obs.obs_property_list_add_string(select_widget, sink, sink)
	end

	obs.obs_properties_add_bool(props, "enable", "Enable")

	return props
end

function script_update(settings)
	enable = obs.obs_data_get_bool(settings, "enable")
	device = obs.obs_data_get_bool(settings, "device")
	if enable then
		if output and device ~= output_device then
			stop_output()
		end
		if not output then
			output = obs.obs_output_create("pulse_output", "pulse_output", settings, None)
			obs.obs_output_start(output)
		end
	else
		if output then
			stop_output()
		end
	end
end

function stop_output()
	if output then
		obs.obs_output_stop(output)
		obs.obs_output_release(output)
		output = nil
		output_device = nil
	end
end

function script_unload()
	stop_output()
end

