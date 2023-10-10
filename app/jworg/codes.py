languages = {
	"U": "Russian",
	}

def language_code_to_name(code):
	return languages.get(code, code)

countries = {
	"FIN": "Finland",
	"UKR": "Ukraine",
	}

def country_code_to_name(code):
	return countries.get(code, code)

