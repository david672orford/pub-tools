"""
Monkey patch obspython
"""

from ctypes import CDLL, Structure, POINTER, cast, c_void_p, c_uint, c_ubyte, c_bool
from ctypes.util import find_library

import obspython as obs

# void obs_frontend_set_current_scene(obs_source_t *scene)
# Rewrap to prevent a lockup if a frontend event handler is installed:
#  https://github.com/obsproject/obs-studio/issues/3385
def wrap_obs_frontend_set_current_scene():
	frontend = CDLL(find_library("obs-frontend-api"))
	cfunc = frontend.obs_frontend_set_current_scene
	cfunc.argtypes = [c_void_p]
	cfunc.restype = None
	def wrapper(scene):
		cfunc(int(scene))
	return wrapper
obs.obs_frontend_set_current_scene = wrap_obs_frontend_set_current_scene()

# bool gs_stagesurface_map(gs_stagesurf_t *stagesurf, uint8_t **data, uint32_t *linesize)
# Rewrap to make usable:
#  https://github.com/upgradeQ/Streaming-Software-Scripting-Reference/blob/master/src/get_source_frame_data_ffi.py
#  https://github.com/obsproject/obs-studio/pull/4779
def wrap_gs_stagesurface_map():
	obsffi = CDLL(find_library("obs"))
	class StageSurf(Structure):
		pass
	cfunc = obsffi.gs_stagesurface_map
	cfunc.restype = c_bool
	cfunc.argtypes = [POINTER(StageSurf), POINTER(POINTER(c_ubyte)), POINTER(c_uint)]
	def wrapper(stagesurf):
		stagesurfp = c_void_p(int(stagesurf))
		stagesurfp = cast(stagesurfp, POINTER(StageSurf))
		data = POINTER(c_ubyte)()
		linesize = c_uint()
		ok = cfunc(stagesurfp, byref(data), byref(linesize))
		if ok:
			return (linesize.value, data)
		else:
			return (None, None)
	return wrapper
obs.gs_stagesurface_map = wrap_gs_stagesurface_map()

