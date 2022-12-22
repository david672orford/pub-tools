function init_dnd()
	{
	function $(id)
		{
		return document.querySelector(id);
		}
	
	function select_all(name, state)
		{
		document.getElementsByName(name).forEach(checkbox => {
			checkbox.checked = state;
			});
		}
	
	document.getElementById("select-all").addEventListener("click", event => { select_all("del",true); });
	document.getElementById("deselect-all").addEventListener("click", event => { select_all("del",false); });
	
	let dropArea = $('.scenes');
	
	/* Allow drop */
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

		$("#files").files = e.dataTransfer.files;
		$("#upload-form").submit();

		dropArea.classList.remove("highlight");
		counter = 0;
		});
	}
