function init_scenes()
	{
	function $(id)
		{
		return document.querySelector(id);
		}

	/* ===============================================================
	   Checkbox for selecting all scenes except those which begin with a star
    */
	$("#check-all").addEventListener("click", function() {
		let state = event.target.checked;
		document.getElementsByName("del").forEach(checkbox => {
			if(!state || checkbox.value[0] != "*")
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
	let dummy_scene = document.createElement("img");
	dummy_scene.src = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

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
		if(over.nodeName == "BUTTON")				/* FIXME: fragile code */
			over = over.parentNode.parentNode;
		else if(over.nodeName == "TD")
			over = over.parentNode;
		/*console.log(moving_scene, over);*/
		if (isBefore(moving_scene, over))
			scenes_list.insertBefore(moving_scene, over);
		else
			scenes_list.insertBefore(moving_scene, over.nextSibling);
		}

	function on_scene_drop(e) {
		console.log("reorder drop");
		e.stopPropagation();
		moving_scene.classList.remove("highlight");
		moving_scene = null;
		scenes_list.removeEventListener("dragenter", on_scene_dragenter);
		scenes_list.removeEventListener("drop", on_scene_drop);
		}

	scenes_list.addEventListener("dragstart", (e) => {
		console.log("reorder dragstart:", e.target);
		//e.stopPropagation();
		e.dataTransfer.effectAllowed = "move";
		e.dataTransfer.setData("text/plain", null);
		e.dataTransfer.setDragImage(dummy_scene, 5, 5);
		moving_scene = e.target;
		moving_scene.classList.add("highlight");
		scenes_list.addEventListener("dragenter", on_scene_dragenter);
		scenes_list.addEventListener("drop", on_scene_drop);
		});

	/* ===============================================================
       Drag-and-drop dropzone for adding scenes
	*/
	let dropArea = $('#scenes');
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
	dropArea.addEventListener('drop', (e) => {
		e.preventDefault();
		console.log(e.dataTransfer);
		console.log("Files:", e.dataTransfer.files);
		console.log("Types:", e.dataTransfer.types);
		console.log("Items:", e.dataTransfer.items);

		if(e.dataTransfer.files.length > 0)			/* local files */
			{
			$("#files").files = e.dataTransfer.files;
			/* $("#upload-form").submit() doesn't trigger Turbo Stream handling */
			$("#upload-form BUTTON[type='submit']").click();
			}
		else
			{
			let i = e.dataTransfer.types.indexOf("text/uri-list");
			if(i != -1)
				{
				e.dataTransfer.items[i].getAsString(function(url) {
					console.log("url:", url);
					$("#add-url").value = url;
					$("#add-url-form BUTTON").click();
					});
				}
			else
				{
				let i = e.dataTransfer.types.indexOf("text/html");
				if(i != -1)
					{
					e.dataTransfer.items[i].getAsString(function(html) {
						console.log("html:", html);
						$("#add-html").value = html;
						$("#add-html-form BUTTON").click();
						});
					}
				}
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

