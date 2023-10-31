function init_patchbay(links) {
	let node_x;
	let node_y;
	let prev_cursor_x;
	let prev_cursor_y;
	let drag_links;
	let temp_link;
	const patchbay = document.getElementById("patchbay");
	const patchbay_svg = patchbay.getElementsByTagName("svg")[0];
	const link_template = patchbay.getElementsByTagName("template")[0];
	const dummy_input = patchbay.getElementsByClassName("dummy-input")[0];

	/* Handles the drawing of one line from an output to an input */
	class LinkDrawer
		{
		constructor(start_el, end_el)
			{
			this.start_el = start_el;
			this.end_el = end_el;
			this.path = link_template.content.cloneNode(true).querySelector("path");
			patchbay_svg.appendChild(this.path);
			if(end_el != null)
				this.position();
			}

		position(pos)
			{
			let pb_rect = patchbay.getBoundingClientRect();
			let rect;

			/* Find the middle of the right edge of the audio output. */
			rect = this.start_el.getBoundingClientRect();
			let start_x = rect.right - pb_rect.left;
			let start_y = (rect.bottom + rect.top) / 2 - pb_rect.top;

			let end_x;
			let end_y;	
			if(this.end_el != null)
				{
				/* Find the middle of the left edge of the audio input. */
				rect = this.end_el.getBoundingClientRect();
				end_x = rect.left - 5 - pb_rect.left;	/* room for arrowhead tip */
				end_y = (rect.bottom + rect.top) / 2 - pb_rect.top;
				}
			else
				{
				end_x = pos[0] - pb_rect.left;
				end_y = pos[1] - pb_rect.top;
				}

			/* Get the bounding box of the SVG curve we will draw in patchbay canvas space */
			const x = Math.min(start_x, end_x);
			const y = Math.min(start_y, end_y);
			const width = Math.abs(end_x - start_x);
			const signed_height = (end_y - start_y);
			const height = Math.abs(signed_height);

			const cp1x = start_x + (width + height) * 0.5;
			const cp1y = start_y - (signed_height * .05);
			const cp2x = end_x - (width + height) * 0.5;
			const cp2y = end_y + (signed_height * .05);
			this.path.setAttribute("d", `M ${start_x} ${start_y} C ${cp1x} ${cp1y} ${cp2x} ${cp2y} ${end_x} ${end_y}`);
			}

		remove()
			{
			this.path.remove();
			}
		}

	/* User is dragging a <div> which represents a Pipewire node */
	function on_node_dragstart(e)
		{
		const node = e.target;
		//console.log("Node Dragstart:", node.id);

		node_x = node.offsetLeft;
		node_y = node.offsetTop;
		prev_cursor_x = e.pageX;
		prev_cursor_y = e.pageY;

		drag_links = [];
		const outputs = node.getElementsByClassName("node-outputs")[0].children;
		for(let i=0; i < outputs.length; i++)
			{
			let output = parseInt(outputs[i].id.split("-")[1]);
			for(let i2=0; i2 < links.length; i2++)
				{
				if(links[i2][0] == output)
					drag_links.push(links[i2]);
				}
			}
		const inputs = node.getElementsByClassName("node-inputs")[0].children;
		for(let i=0; i < inputs.length; i++)
			{
			let input = parseInt(inputs[i].id.split("-")[1]);
			for(let i2=0; i2 < links.length; i2++)
				{
				if(links[i2][1] == input)
					drag_links.push(links[i2]);
				}
			}
		//console.log("drag links:", drag_links);

		e.target.addEventListener("drag", on_node_drag);
		e.target.addEventListener("dragend", on_node_dragend);

		e.dataTransfer.setDragImage(dummy_input, 5, 5);
		}

	/* Fired several times a second as the user moves the node */
	function on_node_drag(e)
		{
		//console.log("Drag:", e.pageX, e.pageY, e);
		const node = e.target;

		if(e.pageX == 0)		/* last event is bad */
			return;

		node_x += (e.pageX - prev_cursor_x);
		node_y += (e.pageY - prev_cursor_y);
		node.style.left = node_x + "px";
		node.style.top = node_y + "px";
		prev_cursor_x = e.pageX;
		prev_cursor_y = e.pageY;

		drag_links.forEach((link) => { link[2].position(); });
		}

	/* User has dropt the node */
	function on_node_dragend(e)
		{
		const node = e.currentTarget;
		//console.log("Node Dragend:", node.id);

		fetch("save-node-pos", {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
				},
			body: JSON.stringify({key: node.dataset.key, x: node_x, y: node_y})
			});

		node.removeEventListener("drag", on_node_drag);
		node.removeEventListener("dragend", on_node_dragend);
		}

	/* Draw an arrow to represent a Pipewire link */
	function draw_link(index)
		{
		const output_port_id = links[index][0];
		const input_port_id = links[index][1];
		const output_port = document.getElementById("port-" + output_port_id);
		const input_port = document.getElementById("port-" + input_port_id);
		if(!output_port || !input_port)
			{
			alert("Link between nodes not displayed:" + links[index]);
			return;
			}
		const link_drawer = new LinkDrawer(output_port, input_port);
		link_drawer.path.addEventListener("click", (e) => {
			link_action("destroy-link", output_port_id, input_port_id);
			});
		links[index].push(link_drawer);
		}

	/* Send a request to the server to have a link created or destroyed.
	   If the request is successful, add or remove the arrow. */
	async function link_action(action, output_port_id, input_port_id)
		{
		//console.log("link_action:", action, output_port_id, input_port_id);

		const response = await fetch(action, {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
				},
			body: JSON.stringify({
				output_port_id: output_port_id,
				input_port_id: input_port_id,
				})
			});

		if(response.ok)
			{
			if(action == "create-link")
				{
				links.push([output_port_id, input_port_id]);
				draw_link(links.length - 1);
				}
			else		/* destroy-link */
				{
				for(let i=0; i < links.length; i++)
					{
					const link = links[i];
					if(link[0] == output_port_id && link[1] == input_port_id)
						{
						links.splice(i, 1);
						link[2].remove();
						break;
						}
					}
				}
			}
		}

	/* Start of dragging of a Pipewire output port */
	function on_port_dragstart(e)
		{
		//console.log("Port Dragstart:", e.target.id);
		e.dataTransfer.setData("text/plain", e.target.id);
		e.stopPropagation();		/* so dragstart won't be called on node */

		e.dataTransfer.setDragImage(dummy_input, 5, 5);
		temp_link = new LinkDrawer(e.target, null);
		temp_link.path.style.pointerEvents = "none";
		
		e.target.addEventListener("drag", on_port_drag);
		e.target.addEventListener("dragend", on_port_dragend);
		}

	function on_port_drag(e)
		{
		//console.log("Port drag:", e.pageX, e.pageY);
		if(e.pageX == 0)		/* last event is bad */
			return;
		temp_link.position([e.pageX, e.pageY]);
		}

	function on_port_dragend(e)
		{
		//console.log("Port Dragend:", e.target.id);
		e.target.removeEventListener("drag", on_port_drag);
		e.target.removeEventListener("dragend", on_port_dragend);
		temp_link.remove()
		temp_link = null;
		dummy_input.style.left = null;
		dummy_input.style.top = null;
		}

	/* Dragged output port hovering over an input port */
	function on_port_dragenter(e)
		{
		e.target.classList.add("highlight");
		}
	function on_port_dragleave(e)
		{
		e.target.classList.remove("highlight");
		}

	/* Dragging over a Pipewire input port */
	function on_port_dragover(e)
		{
		e.preventDefault();
		e.dataTransfer.dropEffect = "link";
		}

	/* Dropped on a Pipewire inport port in order to complete the link */
	function on_port_drop(e)
		{
		e.preventDefault()
		e.target.classList.remove("highlight");

		/* Get the Pipewire port ID numbers of the output and input which we should connect. */
		const output_port_id = e.dataTransfer.getData("text/plain").split("-")[1];
		const input_port_id = e.target.id.split("-")[1];

		/* FIXME: There must be a better way to do this! */
		for(let i=0; i < links.length; i++)
			{
			let link = links[i];
			if(link[0] == output_port_id && link[1] == input_port_id)
				{
				console.log("Duplicate link!");
				return;
				}
			}

		link_action("create-link", output_port_id, input_port_id);
		}

	/* Connect everything up */
	let nodes = document.getElementsByClassName("node");
	for(let i=0; i<nodes.length; i++)
		{
		let node = nodes[i];
		//console.log(i, node.offsetLeft, node.offsetTop);

		node.setAttribute("draggable", "true");
		node.addEventListener("dragstart", on_node_dragstart);

		/* Needed by Firefox but commented out because Firefox has other problems. */
		/*patchbay.addEventListener("dragenter", (e) => { e.preventDefault() });
		patchbay.addEventListener("dragleave", (e) => { e.preventDefault() });*/

		if(node.style.left == "")
			{
			node.style.left = node.offsetLeft + "px";
			node.style.top = node.offsetTop + "px";
			}

		let inputs = node.getElementsByClassName("node-inputs")[0].getElementsByClassName("port");
		for(let i=0; i<inputs.length; i++)
			{
			inputs[i].addEventListener("dragenter", on_port_dragenter);
			inputs[i].addEventListener("dragleave", on_port_dragleave);
			inputs[i].addEventListener("dragover", on_port_dragover);
			inputs[i].addEventListener("drop", on_port_drop);
			}

		let outputs = node.getElementsByClassName("node-outputs")[0].getElementsByClassName("port");
		for(let i=0; i<outputs.length; i++)
			{
			outputs[i].setAttribute("draggable", "true");
			outputs[i].addEventListener("dragstart", on_port_dragstart);
			}
		}

	document.getElementById("patchbay").classList.remove("patchbay-loading");

	/* Draw (possibly curved) arrows to represent the links */
	for(let i=0; i<links.length; i++)
		{
		draw_link(i);
		}
}

