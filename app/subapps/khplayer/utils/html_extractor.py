import lxml.html
import lxml.etree

class HTML:
	delete_links = set(["xrefLink", "footnoteLink"])

	def __init__(self, html):
		self.doc = lxml.html.fromstring(html)

	def cleanup(self):
		for el in self.doc.iter():
			if "style" in el.attrib:
				del el.attrib["style"]
			classes = set(el.attrib.get("class","").split(" "))
			if el.tag == "a" and classes.intersection(self.delete_links):
				#el.getparent().remove(el)
				el.text = None

	def pretty(self):
		return lxml.etree.tostring(self.doc, encoding="UNICODE", pretty_print=True, method="html")

	def text_content(self):
		return self.doc.text_content()

