obs = obslua
bit = require("bit")

source_def = {}
source_def.id = "khplayer-zoom-participant"
source_def.type = obs.OBS_SOURCE_TYPE_INPUT
source_def.output_flags = bit.bor(obs.OBS_SOURCE_VIDEO, obs.OBS_SOURCE_CUSTOM_DRAW)

source_def.get_name = function()
    return "Zoom Participant"
end

source_def.create = function(settings, source)
    local data = {}
    data.source = source
    data.width = 1280
    data.height = 720
    data.parent_source = obs.obs_get_source_by_name("Zoom Capture")
    data.texrender = obs.gs_texrender_create(obs.GS_RGBA, obs.GS_ZS_NONE)
    source_def.update(data, settings)
    return data
end

source_def.destroy = function(data)
	if data.parent_source ~= nil then
		obs.obs_source_release(data.parent_source)
	end
	obs.gs_texrender_destroy(data.texrender)
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
	data.enabled = obs.obs_data_get_bool(settings, "enabled")
    data.crop_x = obs.obs_data_get_int(settings, "crop_x")
    data.crop_y = obs.obs_data_get_int(settings, "crop_y")
    data.crop_width = obs.obs_data_get_int(settings, "crop_width")
    data.crop_height = obs.obs_data_get_int(settings, "crop_height")
end

source_def.video_render = function(data)
	if data.parent_source ~= nil and data.enabled then
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
	else
		print("no source")
    end
end

function script_description()
	return [[
		<h2>KH Player—Zoom Participant Source</h2>
		Adds a "Zoom Participant" source cropped from "Zoom Capture".
		]]
end

obs.obs_register_source(source_def)
