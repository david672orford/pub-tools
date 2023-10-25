iso_languages = {
	"en": "E",
	"ru": "U",
	}

def iso_language_code_to_meps(code):
	return iso_languages[code]

meps_languages = {
	"E": "English",
	"U": "Russian",
	}

def meps_language_code_to_name(code):
	return meps_languages.get(code, code)

meps_countries = {
	"FIN": "Finland",
	"UKR": "Ukraine",
	}

def meps_country_code_to_name(code):
	return meps_countries.get(code, code)

