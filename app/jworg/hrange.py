from lxml import etree as ET
import re
import logging

logger = logging.getLogger(__name__)

class RangeFigure:
	def __init__(self, pnum, el):
		self.id = el.attrib["id"]
		self.pnum = pnum
		self.el = el
	def print(self):
		classes = self.el.attrib.get("class")
		alt = self.el.xpath(".//img")[0].attrib.get("alt")
		print(f"<RangeFigure id={self.id} pnum={self.pnum} classes={repr(classes)} alt={repr(alt[:20])}>")

class HighlightRange:
	excluded_paragraph_types = {
		"qu",		# question
		"figcaption",
		}
	float_figure_classes = {		# figures with these classes belong to the next paragraph
		"east_right",
		"north_center",		# FIXME: not actually floated
		}
	follow_figure_classes = {		# figures with these classes belong to the previous paragraph
		"south_center",
		"dc-bleedToArticleEdge",
		}
	def __init__(self, root):
		context = ET.iterwalk(root, events={"start", "end"}, tag={"h1","h2","h3","h4","h5", "h6", "div", "p"})
		last_pnum = None
		self.figures = []
		for action, el in context:
			#print(f"{action} {el}")

			if action == "start":
				id = el.attrib.get("id", "")

				# Paragraph
				if m := re.match(r"p(\d+)$", id):
					if el.attrib.get("class") not in self.excluded_paragraph_types:
						last_pnum = int(m.group(1))
						for i in reversed(range(len(self.figures))):
							if self.figures[i].pnum is not None:
								break
							self.figures[i].pnum = last_pnum

				# Figure
				elif re.match(r"f\d+$", id):
					classes = set(el.attrib.get("class","").split(" "))
					if classes & self.follow_figure_classes:		# connected to previous paragraph
						figure_pnum = last_pnum
					elif classes & self.float_figure_classes:		# connected to next paragraph
						figure_pnum = None
					else:
						logger.warning("Unrecognized figure position: %s %s", id, str(classes))
						#figure_pnum = 0
						figure_pnum = last_pnum
					self.figures.append(RangeFigure(figure_pnum, el))
					context.skip_subtree()

			# Only connect figures with paragraphs in the same container
			if el.attrib.get("class") == "pGroup" or el.tag == "aside":
				pnum = None

	def print(self):
		for figure in self.figures:
			figure.print()

	def range_figures(self, start, end):
		for figure in self.figures:
			if start <= figure.pnum <= end or figure.pnum == 0:
				yield figure.el

