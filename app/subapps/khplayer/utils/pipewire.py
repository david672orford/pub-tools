import subprocess
import json
from collections import defaultdict

class Device:
	def __init__(self, item, props):
		self.id = item["id"]
		self.name = props["device.name"]
		self.nick = props.get("device.nick")
		self.description = props.get("device.description")

class Node:
	"""Pipewire node with its input and output ports"""
	def __init__(self, item, props):
		self.id = item["id"]
		self.name = props["node.name"]
		self.name_serial = None
		self.nick = props.get("node.nick")
		self.description = props.get("node.description")
		self.is_vu_meter = (props.get("node.rate","") == "1/25")
		for key in ("media.class", "media.type"):	# media.type observed on Telegram's "alsoft" node
			if key in props:
				self.media_class = props[key]
				break
		else:
			self.media_class = ""
		self.inputs = []
		self.outputs = []

	@property
	def label(self):
		if self.nick:
			return self.nick;
		if self.description:
			return self.description;
		return self.name

	def add_port(self, port):
		if port.direction == "input":
			self.inputs.append(port)
		elif port.direction == "output":
			self.outputs.append(port)
		else:
			raise AssertionError

	def find_port_by_name(self, name):
		for direction in (self.inputs, self.outputs):
			for port in direction:
				if port.name == name:
					return port
		return None

	def __repr__(self):
		return "<Node id=%d nick=%s name=%s media_class=%s inputs=%s outputs=%s>" % (
			self.id,
			self.nick,
			self.name,
			self.media_class,
			self.inputs,
			self.outputs,
			)

class Port:
	"""A Pipewire input or an output port"""
	def __init__(self, item, info, props, node):
		self.id = item["id"]
		self.name = props["port.name"]
		self.direction = info["direction"]
		self.node = node
		self.links = []

	def add_link(self, link):
		self.links.append(link)

	def remove_link(self, link):
		self.links.remove(link)

	def __repr__(self):
		return "<Port id=%d name=%s direction=%s>" % (
			self.id,
			self.name,
			self.direction,
			)

class Link:
	"""Connection between an output and an input port"""
	def __init__(self, id, output_port, input_port):
		self.id = id
		self.output_port = output_port
		self.input_port = input_port

	def __repr__(self):
		return "<Link id=%d %s --> %s>" % (
			self.id,
			self.output_port,
			self.input_port,
			)

class Patchbay:
	"""Representation of a Pipewire patchbay"""

	def load(self):
		pwdump = subprocess.Popen(["pw-dump"], stdout=subprocess.PIPE, encoding="utf-8", errors="replace")

		# It is not clear why, but pw-dump's output can contain multiple JSON objects.
		# It is not clear whether this is a bug or not. The additional objects may
		# represent changes. As observed they always contain one item which has
		# nothing but on ID and a null "info".
		pwconf = pwdump.stdout.read()
		pwconf = "[" + pwconf.replace("\n]\n[\n", "\n],\n[\n") + "]"
		#with open("pw-dump.json", "w") as fh:
		#	fh.write(pwconf)
		pwconf = json.loads(pwconf)
		def pwconf_iter():
			for block in pwconf:
				for item in block:
					yield item

		self.devices = []
		self.devices_by_id = {}
		self.nodes_by_id = {}
		self.nodes_by_name = defaultdict(list)
		self.ports_by_id = {}
		self.links = []

		for item in pwconf_iter():
			#print(item["id"], item.get("type"))

			# The body of the record is in the "info" block.
			# Skip null records.
			info = item.get("info",{})
			if info is None:
				continue

			props = info.get("props")

			if item["type"] == "PipeWire:Interface:Device":
				self._add_device(Device(item, props))
			elif item["type"] == "PipeWire:Interface:Node":
				self._add_node(Node(item, props))
			elif item["type"].endswith("PipeWire:Interface:Port"):
				self._add_port(Port(item, info, props, self.nodes_by_id[props["node.id"]]))
			elif item["type"].endswith("PipeWire:Interface:Link"):
				self._add_link(Link(
					item["id"],
					self.ports_by_id[info["output-port-id"]],
					self.ports_by_id[info["input-port-id"]],
					))

		self.nodes = self.nodes_by_id.values()

	def print(self):
		for node in self.nodes:
			if "Audio" in node.media_class:
				print(node)
		for link in self.links:
			print(link)

	def _add_device(self, device):
		self.devices_by_id[device.id] = device
		self.devices.append(device)

	def _add_node(self, node):
		self.nodes_by_id[node.id] = node
		nlist = self.nodes_by_name[node.name]
		nlist.append(node)
		node.name_serial = len(nlist)

	def _add_port(self, port):
		port.node.add_port(port)
		self.ports_by_id[port.id] = port

	def _add_link(self, link):
		link.input_port.add_link(link)
		link.output_port.add_link(link)
		self.links.append(link)

	def _remove_link(self, link):
		link.input_port.remove_link(link)
		link.output_port.remove_link(link)
		self.links.remove(link)

	def find_node(self, **kwargs):
		"""Find the node specified by attributes"""
		class NodeTest:
			def __init__(self, **kwargs):
				self.tests = []
				for name, value in kwargs.items():
					self.tests.append(name)
					setattr(self, name, value)
			def __call__(self, node):
				for test in self.tests:
					if getattr(node, test) != getattr(self, test):
						return False
				return True
		node_test = NodeTest(**kwargs)
		for node in self.nodes:
			if node_test(node):
				return node
		return None

	def find_port(self, port):
		"""Find the port specified by ID, or Nodename:Portname.
		If object is passed, simply return it."""
		if type(port) is Port:
			return port
		if type(port) is str:
			if not ":" in port:
				raise ValueError(port)
			node_name, port_name = port.split(":",1)
			node = self.find_node(name=node_name)
			return node.find_port_by_name(port_name)
		return self.ports_by_id[port]

	def find_link(self, output_port_id, input_port_id):
		"""Find the link specified by the ID's of the ports it connects"""
		for link in self.links:
			if link.output_port.id == output_port_id and link.input_port.id == input_port_id:
				return link
		return None

	def create_link(self, output_port, input_port):
		"""Create a link between an output and an input. Both are specified
		in any format understood by .find_port()."""
		output_port = self.find_port(output_port)
		input_port = self.find_port(input_port)

		# Skip if this link already exists
		for link in self.links:
			if link.output_port is output_port and link.input_port is input_port:
				return

		link = Link(None,  output_port, input_port)
		cmd = ["pw-link", str(link.output_port.id), str(link.input_port.id)]
		subprocess.run(cmd, check=True)
		self._add_link(link)

	def destroy_link(self, output_port=None, input_port=None, link=None):
		if link is None:
			link = self.find_link(output_port, input_port)
		cmd = ["pw-link", "-d", str(link.id)]
		subprocess.run(cmd, check=True)
		self._remove_link(link)
