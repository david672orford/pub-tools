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
		console.log("Items:", e.dataTransfer.items);
		console.log("Types:", e.dataTransfer.types);

		if(e.dataTransfer.files.length > 0)
			{
			$("#files").files = e.dataTransfer.files;
			$("#upload-form").submit();
			}
		else
			{
			let list = e.dataTransfer.items;
			for(let i=0; i < list.length; i++)
				{
				console.log(list[i]);
				list[i].getAsString(s => console.log(s));
				}
			}

		dropArea.classList.remove("highlight");
		counter = 0;
		});
	}

