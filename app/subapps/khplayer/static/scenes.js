function init_scenes()
	{
	function $(id)
		{
		return document.querySelector(id);
		}

	/* ===============================================================
	   Click on scene
    */
	$("#scenes-list").addEventListener("click", (e) => {
		let target = e.target;
		console.log("Click:", target);
		if(target.tagName == "INPUT")	/* checkbox */
			return;
		while(target.tagName != "TR")
			target = target.parentElement;
		target.classList.add("active");
		let data = new FormData();
		data.append("scene", target.id.slice(6));
		fetch("submit", {
			body: data,
			method: "POST",
		});
	});

	/* ===============================================================
	   Checkbox for selecting all scenes except those which begin with a star
    */
	$("#check-all").addEventListener("click", function() {
		let state = event.target.checked;
		Array.from($("#scenes-list").children).forEach(scene => {
			let checkbox = scene.getElementsByTagName("input")[0];
			let scene_name = scene.getElementsByClassName("scene-name")[0];
			if(!state || scene_name.textContent.trim()[0] != "*")
				checkbox.checked = state;
			});
		});

	/* ===============================================================
	   Drag-and-drop to reorder scenes
	   When a drag operation starts here we install handlers which
	   mask the handlers for file drop.
    */
	let scenes_list = $("#scenes-list");
	let moving_scene = null;
	let dummy_image = document.createElement("img");
	dummy_image.src = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

	function isBefore(el1, el2) {
		if(el2.parentNode === el1.parentNode)
			for (let cur = el1.previousSibling; cur && cur.nodeType !== 9; cur = cur.previousSibling)
				if (cur === el2)
					return true;
		return false;
		}

	function on_scene_dragenter(e) {
		console.log("reorder dragenter:", e.target);
		e.stopPropagation();
		let over = e.target;
		while(over.tagName != "TR")
			over = over.parentElement;
		if (isBefore(moving_scene, over))
			scenes_list.insertBefore(moving_scene, over);
		else
			scenes_list.insertBefore(moving_scene, over.nextSibling);
		}

	function on_scene_drop(e) {
		console.log("reorder drop");
		e.stopPropagation();

		fetch("move-scene", {
			method: "POST",
			headers: {
				"Content-Type": "application/json"
				},
			body: JSON.stringify({
				uuid: moving_scene.id.slice(6),
				new_pos: Array.from(moving_scene.parentElement.children).indexOf(moving_scene),
				})
			});

		moving_scene.classList.remove("highlight");
		moving_scene = null;
		scenes_list.removeEventListener("dragenter", on_scene_dragenter);
		scenes_list.removeEventListener("drop", on_scene_drop);
		}

	scenes_list.addEventListener("dragstart", (e) => {
		console.log("reorder dragstart:", e.target);
		let target = e.target;
		while(target.tagName != "TR")
			target = target.parentElement;
		//e.stopPropagation();
		e.dataTransfer.effectAllowed = "move";
		e.dataTransfer.setData("text/plain", null);
		e.dataTransfer.setDragImage(dummy_image, 0, 0);
		moving_scene = target;
		moving_scene.classList.add("highlight");
		scenes_list.addEventListener("dragenter", on_scene_dragenter);
		scenes_list.addEventListener("drop", on_scene_drop);
		});

	/* ===============================================================
	   Reload previews on hover
    */
	function on_row_mouseover(e) {
		let row = e.target;
		fetch("refresh-thumbnail", {
			headers: {
				"Content-Type": "application/json"
				},
			body: JSON.stringify({
				uuid: row.id.slice(6),
				}),
			method: "POST",
		});
	}
	function init_rows(rows) {
		for(let i = 0; i < rows.length; i++) {
			let row = rows[i];
			row.addEventListener("mouseenter", on_row_mouseover);
		}
	}
	init_rows(scenes_list.children);
	let observer = new MutationObserver((mutationList) => {
		if(mutationList.addedNodes)
			init_rows(mutationList.addedNodes);
		});
	observer.observe(scenes_list, {childList: true});

	/* ===============================================================
       Drag-and-drop dropzone for adding scenes
	*/
	let dropArea = $("#scenes-scroller");
	dropArea.addEventListener("dragover", (e) => e.preventDefault());

	/* Visual feedback when over drop zone */
	let counter = 0;
	dropArea.addEventListener("dragenter", (e) => {
		counter++;
		if(counter == 1)
			dropArea.classList.add("highlight");
		e.preventDefault();
		});
	dropArea.addEventListener("dragleave", (e) => {
		counter--;
		if(counter == 0)
			dropArea.classList.remove("highlight");
		e.preventDefault();
		});

	dropArea.addEventListener("dragover", (e) => {
		e.preventDefault();
		});

	/* File actually dropped onto the drop zone */
	dropArea.addEventListener("drop", (e) => {
		e.preventDefault();
		console.log(e.dataTransfer);
		console.log("Types:", e.dataTransfer.types);
		console.log("Files:", e.dataTransfer.files);

		/* Pick a drag-n-drop type we support, insert the data into the
		   appropriate form, and submit it. Note that we submit the
		   form using .click() because .submit() does not trigger
		   Turbo Stream handling. */
		let i;
		if((i = e.dataTransfer.types.indexOf("text/html")) != -1)				/* preference 1, the most information */
			{
			e.dataTransfer.items[i].getAsString(function(html) {
				console.log("html:", html);
				$("#add-html").value = html;
				$("#add-html-form BUTTON").click();
				});
			}
		else if((i = e.dataTransfer.types.indexOf("text/uri-list")) != -1)		/* preference 2, explicit */
			{
			e.dataTransfer.items[i].getAsString(function(url) {
				console.log("url:", url);
				$("#add-url").value = url;
				$("#add-url-form BUTTON").click();
				});
			}
		else if((i = e.dataTransfer.types.indexOf("text/plain")) != -1)			/* preference 3, ambiguous */
			{
			e.dataTransfer.items[i].getAsString(function(text) {
				console.log("text:", text);
				$("#add-text").value = text;
				$("#add-text-form BUTTON").click();
				});
			}
		else if(e.dataTransfer.files.length > 0)			/* local files */
			{
			$("#files").files = e.dataTransfer.files;
			$("#upload-form BUTTON[type='submit']").click();
			}
		else
			{
			alert("No supported dataTransfer type");
			}

		dropArea.classList.remove("highlight");
		counter = 0;
		});

	/* ===============================================================
	   Hook up the replacements for the ugly file chooser
	*/
	let file_upload = $(".file-upload");
	let file_input = file_upload.querySelector("INPUT[type='file']");
	file_input.addEventListener("change", (event) => {
		let files = event.target;
		let ul = files.parentElement.getElementsByTagName("ul")[0];
		while(ul.firstChild)
			{
			ul.removeChild(ul.firstChild);
			}
		for(let i=0; i < files.files.length; i++)
			{
			let li = document.createElement("li");
			li.textContent = files.files[i].name;
			ul.append(li);
			}
		});
	file_upload.querySelector("BUTTON").addEventListener("click", (event) => {
		file_input.click();
		});

	}

/* Scene event handler sometimes inserts <script> tags which call these functions */
function set_current_scene(className, uuid) {
	console.log("set_current_scene:", className, uuid);
	document.currentScript.remove();
	Array.from(document.getElementById("scenes-list").children).forEach(row => {
		if(uuid && row.id == "scene-" + uuid)
			row.classList.add(className);
		else
			row.classList.remove(className);
		row.classList.remove("active");
		});
	}

function init_scene_composer() {

Array.from(document.getElementsByTagName("form")).forEach(form_el => {

	if(!form_el.elements.enabled)
		return

	/* Enable checkbox */
	form_el.elements.enabled.addEventListener("change", (event) => {
		post_set_enabled(form_el);
		});

	/* Face button */
	form_el.getElementsByClassName("face")[0].addEventListener("click", (event) => {
		post_ptz(form_el, false, event.target.value);
		});

	/* Reset button */
	form_el.getElementsByClassName("reset")[0].addEventListener("click", (event) => {
		form_el.x.value = "50";
		form_el.y.value = "50";
		form_el.zoom.value = "1.0";
		post_ptz(form_el, false, null);
		});

	/* PTZ sliders */
	Array.from(form_el.getElementsByClassName("slider")).forEach(slider => {
		let input = slider.getElementsByTagName("input")[0];
		let span = slider.getElementsByTagName("span")[0];
		span.textContent = input.value;
		input.addEventListener("input", (event) => {
			span.textContent = event.target.value;
			post_ptz(form_el, false, null);
			});
		});

	/* Bounds buttons */
	Array.from(form_el.getElementsByClassName("bounds")).forEach(position => {
		Array.from(position.getElementsByTagName("button")).forEach(button => {
			button.addEventListener("click", (event) => {
				form_el.bounds.value = event.target.value;
				post_ptz(form_el, true, null);
				});
			});
		});

	});

function post_set_enabled(form_el) {
	console.log(form_el, form_el.enabled);
	fetch("set-enabled", {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
			},
		body: JSON.stringify({
			id: parseInt(form_el.id.slice(10)), /* "sceneitem" */
			enabled: form_el.enabled.checked,
			})
		});
	}

async function post_ptz(form_el, new_bounds, face_source_uuid) {
	let response = await fetch("ptz", {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
			},
		body: JSON.stringify({
			id: parseInt(form_el.id.slice(10)), /* "sceneitem" */
			bounds: form_el.bounds.value,
			new_bounds: new_bounds,
			dimensions: form_el.dimensions.value,
			x: parseInt(form_el.x.value),
			y: parseInt(form_el.y.value),
			zoom: parseFloat(form_el.zoom.value),
			face_source_uuid: face_source_uuid,
			})
		});
	let result = await response.json();
	console.log("result:", result);
	form_el.x.value = result["x"];
	form_el.y.value = result["y"];
	form_el.zoom.value = result["zoom"];
	}

}

