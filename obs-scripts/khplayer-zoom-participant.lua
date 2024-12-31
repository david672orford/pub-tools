obs = obslua
bit = require("bit")

source_def = {}
source_def.id = "khplayer-zoom-participant"
source_def.type = obs.OBS_SOURCE_TYPE_INPUT
source_def.output_flags = bit.bor(obs.OBS_SOURCE_VIDEO, obs.OBS_SOURCE_CUSTOM_DRAW, obs.OBS_SOURCE_CONTROLLABLE_MEDIA)

source_def.get_name = function()
	return "Zoom Participant"
end

source_def.create = function(settings, source)
	local data = {}
	data.name = obs.obs_source_get_name(source)
	print("Source create: " .. data.name)
	data.source = source
	data.width = 1280
	data.height = 720
	data.parent_source_name = "Zoom Capture"
	data.parent_source = obs.obs_get_source_by_name(data.parent_source_name)
	if data.parent_source ~= nil then
   		if obs.obs_source_showing(source) then
			obs.obs_source_inc_showing(data.parent_source)
		end
		if obs.obs_source_active(source) then
	 		obs.obs_source_inc_active(data.parent_source)
	 	end
	end
	data.texrender = obs.gs_texrender_create(obs.GS_RGBA, obs.GS_ZS_NONE)
	source_def.update(data, settings)
	return data
end

source_def.destroy = function(data)
	print("Source destroy: " .. data.name)
	if data.parent_source ~= nil then
		obs.obs_source_release(data.parent_source)
		data.parent_source = nil
	end
	obs.gs_texrender_destroy(data.texrender)
end

source_def.show = function(data)
	print("Source showing: " .. data.name)
	if data.parent_source == nil then
		data.parent_source = obs.obs_get_source_by_name(data.parent_source_name)
	end
	if data.parent_source ~= nil then
		obs.obs_source_inc_showing(data.parent_source)
	end
end

source_def.hide = function(data)
	print("Source hidden: " .. data.name)
	if data.parent_source ~= nil then
		obs.obs_source_dec_showing(data.parent_source)
	end
end

source_def.activate = function(data)
	print("Source activated: " .. data.name)
	if data.parent_source ~= nil then
		obs.obs_source_inc_active(data.parent_source)
	end
end

source_def.deactivate = function(data)
	print("Source deactivated: " .. data.name)
	if data.parent_source ~= nil then
		obs.obs_source_dec_active(data.parent_source)
	end
end

source_def.get_width = function(data)
	return data.width
end

source_def.get_height = function(data)
	return data.height
end

source_def.get_defaults = function(settings)
	obs.obs_data_set_default_bool(settings, "enabled", true)
	obs.obs_data_set_default_int(settings, "crop_x", 0)
	obs.obs_data_set_default_int(settings, "crop_y", 0)
	obs.obs_data_set_default_int(settings, "crop_width", 1280)
	obs.obs_data_set_default_int(settings, "crop_height", 720)
end

source_def.get_properties = function(data)
	local props = obs.obs_properties_create()
	obs.obs_properties_add_bool(props, "enabled", "Enabled")
	obs.obs_properties_add_int(props, "crop_x", "Crop X", 0, 3840, 1)
	obs.obs_properties_add_int(props, "crop_y", "Crop Y", 0, 2160, 1)
	obs.obs_properties_add_int(props, "crop_width", "Crop Width", 320, 1280, 1)
	obs.obs_properties_add_int(props, "crop_height", "Crop Height", 180, 720, 1)
	return props
end

source_def.update = function(data, settings)
	print("Source update: " .. data.name)
	data.enabled = obs.obs_data_get_bool(settings, "enabled")
	data.crop_x = obs.obs_data_get_int(settings, "crop_x")
	data.crop_y = obs.obs_data_get_int(settings, "crop_y")
	data.crop_width = obs.obs_data_get_int(settings, "crop_width")
	data.crop_height = obs.obs_data_get_int(settings, "crop_height")
end

source_def.video_render = function(data)
	if data.enabled then
		if data.parent_source ~= nil then
			if obs.gs_texrender_begin(data.texrender, data.crop_width, data.crop_height) then
				obs.gs_ortho(0.0, data.crop_width, 0.0, data.crop_height, -100.0, 100.0)
				obs.gs_matrix_translate3f(-data.crop_x, -data.crop_y, 0.0)
		   		obs.obs_source_video_render(data.parent_source)
			 	obs.gs_texrender_end(data.texrender)
				local tex = obs.gs_texrender_get_texture(data.texrender)
				local effect = obs.obs_get_base_effect(obs.OBS_EFFECT_DEFAULT)
		  		while obs.gs_effect_loop(effect, "Draw") do
					obs.obs_source_draw(tex, 0, 0, data.width, data.height, false)
		   		end
		  		obs.gs_texrender_reset(data.texrender)
			end
		-- else
		--	print("Zoom Capture source missing")
		end
	end
end

function script_description()
	return [[
		<h2>KH Player—Zoom Participant Source</h2>
		Adds a "Zoom Participant" source cropped from "Zoom Capture".
		]]
end

obs.obs_register_source(source_def)
