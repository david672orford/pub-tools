"""
Rewrap obs.gs_stagesurface_map using Ctypes
"""

from ctypes import *
from ctypes.util import find_library
import obspython as obs

def wrap_gs_stagesurface_map():
	obsffi = CDLL(find_library("obs"))
	class StageSurf(Structure):
		pass
	_gs_stagesurface_map = getattr(obsffi, "gs_stagesurface_map")
	_gs_stagesurface_map.restype = c_bool
	_gs_stagesurface_map.argtypes = [POINTER(StageSurf), POINTER(POINTER(c_ubyte)), POINTER(c_uint)]
	def gs_stagesurface_map(stagesurf):
		stagesurfp = c_void_p(int(stagesurf))
		stagesurfp = cast(stagesurfp, POINTER(StageSurf))
		data = POINTER(c_ubyte)()
		linesize = c_uint()
		ok = _gs_stagesurface_map(stagesurfp, byref(data), byref(linesize))
		if ok:
			return (linesize.value, data)
		else:
			return (None, None)
	return gs_stagesurface_map
obs.gs_stagesurface_map = wrap_gs_stagesurface_map()
