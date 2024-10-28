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
		alt = self.el.xpath(".//img")[0].attrib.get("alt")
		print(f"<RangeFigure id={self.id} pnum={self.pnum} alt={repr(alt[:50])}>")

class HighlightRange:

	# <p> tags with these classes can be ignored
	excluded_paragraph_types = {
		"qu",			# printed study question 
		"figcaption",	# for formatting a picture caption
		}

	# figures with these classes belong to the next paragraph
	leading_figure_classes = {
		"north_center",				# centered above paragraph
		"east_right",				# float right
		"du-float--inlineEnd",
		}

	# figures with these classes belong to the previous paragraph
	following_figure_classes = {
		"south_center",				# centered below paragraph
		}

	# Illustrations are associated with the first paragraph in this group
	columns_classes = {
		"dc-columns",
		"dc-columns-desktopOnly",
		"dc-bleedToArticleEdge",
		}

	# Trailing illustrations are associated with the last paragraph in this group
	pgroup_classes = {
		"pGroup",					# a subheading
		"aside",					# a box
		}

	def __init__(self, article):
		self.top_image = article.main_tag.find(".//figure[@id='articleTopRelatedImage']")

		context = ET.iterwalk(article.article_tag, events={"start", "end"}, tag={"h1","h2","h3","h4","h5", "h6", "div", "p"})
		first_pnum = None
		last_pnum = None
		stack = []
		self.figures = []
		for action, el in context:
			id = el.attrib.get("id", "")
			classes = set(el.attrib.get("class","").split(" "))

			if action == "start":

				# Paragraph
				if m := re.match(r"p(\d+)$", id):
					if not (classes & self.excluded_paragraph_types):
						last_pnum = int(m.group(1))
						if first_pnum is None:
							first_pnum = last_pnum
						self.sweep_figures(last_pnum, "next")
					print(f"paragraph {id} first_pnum={first_pnum} last_pnum={last_pnum}")
					context.skip_subtree()

				# Figure
				elif re.match(r"f\d+$", id):
					if classes & self.following_figure_classes:		# connected to previous paragraph
						figure_pnum = last_pnum
					elif classes & self.leading_figure_classes:		# connected to next paragraph
						figure_pnum = "next"
					else:											# connected to first paragraph in paragraph group container
						figure_pnum = "neighbor"
					print(f"figure {id} {figure_pnum}")
					self.figures.append(RangeFigure(figure_pnum, el))
					context.skip_subtree()

				elif classes & self.pgroup_classes:
					print()
					print(f"start of pgroup: {el.tag} {id}")
					stack.append(first_pnum)
					first_pnum = last_pnum = None
				elif classes & self.columns_classes:
					print()
					print(f"start of columns: {el.tag} {id}")
					stack.append(first_pnum)
					first_pnum = last_pnum = None

			elif action == "end":
				if re.match(r"p(\d+)$", id):
					pass
				elif re.match(r"f\d+$", id):
					pass
				elif classes & self.pgroup_classes:
					print(f"end of pgroup {el.tag} {id} first_pnum={first_pnum} last_pnum={last_pnum}")
					print()
					self.sweep_figures(last_pnum, "neighbor")
					first_pnum = stack.pop(-1)
					last_pnum = None
				elif classes & self.columns_classes:
					print(f"end of columns {el.tag} {id} first_pnum={first_pnum} last_pnum={last_pnum}")
					print()
					self.sweep_figures(first_pnum, "neighbor")
					first_pnum = stack.pop(-1)
					last_pnum = None

		# Look for figures which did not get connected
		for figure in self.figures:
			if type(figure.pnum) is str:
				figure.pnum = 0

	def sweep_figures(self, pnum, placeholder):
		print(f"sweep_figures({pnum}, {placeholder})")
		assert pnum is not None
		for i in reversed(range(len(self.figures))):
			if self.figures[i].pnum != placeholder:
				break
			print(f" assigning {self.figures[i].id} to {pnum}")
			self.figures[i].pnum = pnum

	def print(self):
		for figure in self.figures:
			figure.print()

	def range_figures(self, start, end):
		for figure in self.figures:
			if start <= figure.pnum <= end:
				yield figure

