import re

# Convert a time in seconds into a string such as "4:45" or even "1:04:45"
def time_to_str(seconds):
	hours = int(seconds / 3600)
	seconds = seconds % 3600
	minutes = int(seconds / 60)
	seconds = seconds % 60
	if hours > 0:
		return "%d:%02d:%02d" % (hours, minutes, seconds)
	else:
		return "%d:%02d" % (minutes, seconds)

# Parse a time string such as "4:45" into seconds
def parse_time(timestr):
	elements = timestr.split(":")
	if not 0 < len(elements) <= 3:
		raise ValueError
	seconds = 0
	for element in elements:
		if not re.match(r"^\d?\d$", element):
			raise ValueError
		value = int(element)
		if not 0 <= value < 60:
			raise ValueError
		seconds = (seconds * 60) + value
	return seconds

