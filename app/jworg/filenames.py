import re

def is_jworg_filename(filename):
	return jworg_filename_category(filename) is not None

def jworg_filename_category(filename):
	if filename.startswith("sjjm_") and filename.endswith(".mp4"):	# songbook
		return "song"
	elif re.match(r"^\d\d\d\d+_.+\.jpg$", filename):
		return "image"
	elif re.match(r"^[a-zA-Z0-9]+[_-].+_r\d+P\.mp4$", filename):	# mwbv_U_202111_03_r480P.mp4
		return "video"
	elif re.match(r"^[a-z]+_[A-Z].+\.pdf$", filename):				# g_U_202411.pdf
		return "pdf"
	return None
