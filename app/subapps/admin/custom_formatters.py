from markupsafe import Markup, escape
import json

# Pretty print JSON
def format_json(view, context, model, name):
	value = getattr(model, name)
	text = escape(json.dumps(value, indent=2, ensure_ascii=False))
	markup = Markup("<pre>%s</pre>" % text)
	return markup

