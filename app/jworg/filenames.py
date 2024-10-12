import re

def is_jworg_filename(filename):
	if filename.startswith("sjjm_") and filename.endswith(".mp4"):	# songbook
		return True
	elif re.match(r"^\d\d\d\d+_.+\.jpg$", filename):
		return True
	elif re.match(r"^[a-zA-Z0-9]+[_-].+_r\d+P\.mp4$", filename):	# mwbv_U_202111_03_r480P.mp4
		return True
	return False

