# EPUB Loader
# https://en.wikipedia.org/wiki/EPUB

import zipfile
from lxml import etree as ET
from lxml.builder import E
import lxml.html

namespaces = {
	'n':'urn:oasis:names:tc:opendocument:xmlns:container',
	'opf':'http://www.idpf.org/2007/opf',
	'daisy':'http://www.daisy.org/z3986/2005/ncx/',
	'dc':'http://purl.org/dc/elements/1.1/',
	'xhtml':'http://www.w3.org/1999/xhtml',
	}

# Read information out of an Epub file.
class EpubLoader:
	def __init__(self, filename, toc_range=None):
		self.filename = filename
		self.epub = zipfile.ZipFile(filename)

		# Get the path to the OPF file out of META-INF/container.xml.
		# Set the rootdir to its dirname.
		self.rootdir = "META-INF"
		opf_file_path = self.load_xml("container.xml").find("./n:rootfiles/n:rootfile", namespaces).get('full-path')
		self.rootdir, opf_file_path = opf_file_path.rsplit("/",1)

		# Extract OPF metadata
		self.opf = EpubOpf(self, opf_file_path)

	# Open one of the files withing the Epub file.
	# Return a handle and the file size.
	def open(self, filename):
		file_info = self.epub.getinfo("%s/%s" % (self.rootdir, filename))
		return (self.epub.open(file_info), file_info.file_size)

	# Open one of the files withing the Epub file.
	# Parse it as XML and return an entity tree.
	def load_xml(self, filename):
		data, content_length = self.open(filename)
		return ET.parse(data)

	# Open one of the files within the Epub file.
	# Parse it as HTML and return the root element.
	# Note that in Epub version 2 the content files are actually in XHTML format.
	# According to this:
	#   https://lxml.de/parsing.html
	# we should parse them as XML to avoid "unexpected results", but if we do
	# we get namespaces and we lose all the HTML element methods described here:
	#   https://lxml.de/lxmlhtml.html
	def load_html(self, filename):
		data, content_length = self.open(filename)
		root = lxml.html.parse(data).getroot()
		#for el in root.getiterator():
		#	el.tag = ET.QName(el).localname
		return root

class EpubOpf:
	def __init__(self, epub, opf_file_path):
		opf_el = epub.load_xml(opf_file_path)

		# The manifest lists the files which make up the e-book. This includes not
		# just files containing the text of the book, but also image and style files.
		self.manifest_by_href = {}
		self.manifest_by_id = {}
		for item in opf_el.find("./opf:manifest", namespaces).findall("./opf:item", namespaces):
			item = EpubManifestItem(item.get('id'), item.get('href'), item.get('media-type'))
			self.manifest_by_id[item.id] = item
			self.manifest_by_href[item.href] = item

		# Extract document metadata
		metadata_el = opf_el.find("./opf:metadata", namespaces)
		self.title = metadata_el.find("./dc:title", namespaces).text
		self.cover_image = self.manifest_by_id[
			metadata_el.find("./opf:meta[@name='cover']", namespaces).get('content')
			].href

		# If there is an NPX table of contents file, load it.
		# Otherwise load a primative table of contents from the <spine> element.
		spine_el = opf_el.find("./opf:spine", namespaces)
		self.toc = []
		self.toc_by_title = {}
		ncx_id = spine_el.get('toc')
		if ncx_id is not None:
			for item in epub.load_xml(self.manifest_by_id[ncx_id].href).find("./daisy:navMap", namespaces).findall("./daisy:navPoint", namespaces):
				nav_point = EpubTocItem(
					item.attrib.get('id'),
					item.find("./daisy:navLabel/daisy:text", namespaces).text,	# title
					item.find("./daisy:content", namespaces).get('src')			# filename
					)
				self.toc_by_title = nav_point.title
				self.toc.append(nav_point)
		else:
			for item in spine_el.findall("./itemref"):
				if item.attrib.get("linear", "yes") == "yes":
					nav_point = EpubTocItem(item.attrib.get('id'), None, self.manifest_by_id[item.attrib.get(idref)])
					self.toc.append(nav_point)

class EpubManifestItem:
	def __init__(self, id, href, mimetype):
		self.id = id
		self.href = href
		self.mimetype = mimetype
	def __str__(self):
		return "<EpubManifestItem id=%s href=\"%s\" mimetype=%s>" % (self.id, self.href, self.mimetype)

class EpubTocItem:
	def __init__(self, id, title, href):
		self.id = id
		self.title = title
		self.href = href
	def __str__(self):
		return "<EpubTocItem id=%s title=\"%s\" href=\"%s\">" % (self.id, self.title, self.href)

if __name__ == "__main__":
	import sys
	epub = EpubLoader(sys.argv[1])
	print("Title:", epub.opf.title)
	print("Cover Image:", epub.opf.cover_image)
	for item in epub.opf.manifest_by_id.values():
		print(item)
	for item in epub.opf.toc:
		print(item)

