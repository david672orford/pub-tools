function init_scenes()
	{
	function $(id)
		{
		return document.querySelector(id);
		}

	$("#check-all").addEventListener("click", function() {
		let state = event.target.checked;
		document.getElementsByName("del").forEach(checkbox => {
			if(!state || checkbox.value[0] != "*")
				checkbox.checked = state;
			});
		});

	/* Enable the drag-and-drop dropzone */
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
			$("#upload-form").submit();
			}
		else
			{
			let i = e.dataTransfer.types.indexOf("text/uri-list");
			if(i != -1)
				{
				e.dataTransfer.items[i].getAsString(function(url) {
					console.log("url:", url);
					$("#add-url").value = url;
					$("#add-url-form").submit();
					});
				}
			else
				{
				let i = e.dataTransfer.types.indexOf("text/html");
				if(i != -1)
					{
					e.dataTransfer.items[i].getAsString(function(html) {
						console.log("html:", html);
						});
					}
				}
			}

		dropArea.classList.remove("highlight");
		counter = 0;
		});
	}

