function init_patchbay(links) {
	let node_x;
	let node_y;
	let prev_cursor_x;
	let prev_cursor_y;
	let temp_link;
	let dummy = document.getElementById("dummy");

	function on_node_dragstart(e)
		{
		const node = e.target;
		console.log("Node Dragstart:", node.id);

		node_x = node.offsetLeft;
		node_y = node.offsetTop;
		prev_cursor_x = e.pageX;
		prev_cursor_y = e.pageY;

		e.target.addEventListener("drag", on_node_drag);
		e.target.addEventListener("dragend", on_node_dragend);

		e.dataTransfer.setDragImage(dummy, 0, 0);
		}

	function on_node_drag(e)
		{
		//console.log("Drag:", e);
		const node = e.target;

		if(e.pageX == 0)		/* last event is bad */
			return;

		node_x += (e.pageX - prev_cursor_x);
		node_y += (e.pageY - prev_cursor_y);
		node.style.left = node_x + "px";
		node.style.top = node_y + "px";
		prev_cursor_x = e.pageX;
		prev_cursor_y = e.pageY;

		links.forEach((link) => { link[2].position(); });
		}

	function on_node_dragend(e)
		{
		const node = e.target;
		console.log("Node Dragend:", node.id);

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
		const leader_line = new LeaderLine(
			document.getElementById("port-" + output_port_id),
			document.getElementById("port-" + input_port_id),
			);
		leader_line.setOptions({startSocket: 'right', endSocket: 'left'});
		const svg = document.body.querySelector("svg.leader-line:last-of-type");
		svg.addEventListener("click", (e) => {
			link_action("destroy-link", output_port_id, input_port_id);
			});
		links[index].push(leader_line);
		}

	/* Send a request to the server to have a link created or destroyed.
	   If the request is successful, add or remove the arrow. */
	async function link_action(action, output_port_id, input_port_id)
		{
		console.log("link_action:", action, output_port_id, input_port_id);
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
		console.log("Port Dragstart:", e.target.id);
		e.dataTransfer.setData("text/plain", e.target.id);
		e.stopPropagation();		/* so dragstart won't be called on node */

		e.dataTransfer.setDragImage(dummy, 0, 0);

		temp_link = new LeaderLine(e.target, dummy);
		
		e.target.addEventListener("drag", on_port_drag);
		e.target.addEventListener("dragend", on_port_dragend);
		}

	function on_port_drag(e)
		{
		dummy.style.left = e.pageX + "px";
		dummy.style.top = e.pageY + "px";
		temp_link.position()
		}

	function on_port_dragend(e)
		{
		console.log("Port Dragend:", e.target.id);
		e.target.removeEventListener("drag", on_port_drag);
		e.target.removeEventListener("dragend", on_port_dragend);
		temp_link.remove()
		temp_link = null;
		}

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
		//console.log("dragover");
		e.preventDefault();
		e.dataTransfer.dropEffect = "link";
		}

	/* Dropped on a Pipewire inport port in order to complete the link */
	function on_port_drop(e)
		{
		e.preventDefault()
		const output_port_id = e.dataTransfer.getData("text/plain").split("-")[1];
		const input_port_id = e.target.id.split("-")[1];
		link_action("create-link", output_port_id, input_port_id);
		e.target.classList.remove("highlight");
		}

	/* Connect everything up */
	let nodes = document.getElementsByClassName("node");
	for(let i=0; i<nodes.length; i++)
		{
		let node = nodes[i];
		console.log(i, node.offsetLeft, node.offsetTop);

		node.setAttribute("draggable", "true");
		node.addEventListener("dragstart", on_node_dragstart);

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

