# Enable enabled PulseAudio output for virtual camera

obs = obslua
saved_settings = nil
output = nil

function script_description()
	return "<h2>Virtual Camera Audio</h2><p>Start and stop PulseAudio virtual cable with virtual camera</p>"
end

function script_defaults(settings)
	obs.obs_data_set_default_string(settings, "device", "obs-vcam")
	obs.obs_data_set_default_string(settings, "description", "OBS Virtual Camera")
end

function script_load(settings)
	saved_settings = settings
	obs.obs_frontend_add_event_callback(on_event)
end

function on_event(event)
	print("event: " .. event)
	if event == obs.OBS_FRONTEND_EVENT_VIRTUALCAM_STARTED then
		device = obs.obs_data_get_string(saved_settings, "device")
		output = obs.obs_output_create("pulse_output", device, saved_settings, None)
		obs.obs_output_start(output)
	elseif event == obs.OBS_FRONTEND_EVENT_VIRTUALCAM_STOPPED then
		stop_output()
	end
end

function stop_output()
	print("Stopping audio output")
	if output then
		obs.obs_output_stop(output)
		obs.obs_output_release(output)
		output = nil
	end
end

function script_unload()
	stop_output()
end
