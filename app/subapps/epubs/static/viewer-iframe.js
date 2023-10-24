/* Handler for <a> element which points to a footnote fragment */
function popup(event)
	{
	event.preventDefault();
	event.stopPropagation();
	let id = event.target.getAttribute("href").substring(1);
	let aside = document.getElementById(id).parentElement;
	aside.className = "viewer-popup";
	aside.style.top = event.target.offsetTop + "px";
	}

function init_viewer()
	{
	/* Add the handler to each footnote marker */
	let body = document.getElementsByClassName("bodyTxt");
	if(body.length > 0)
		{
		let links = body[0].getElementsByTagName("a");
		for(let i=0; i < links.length; i++)
			{
			let link = links[i];
			if(link.getAttribute("epub:type") == "noteref")
				{
				link.addEventListener("click", popup);
				}
			}
	
		/* Hide the footnotes whenever the user clicks outside a footnote */
		document.addEventListener("click", function(event) {
			let asides = document.getElementsByClassName("groupExt")[0].getElementsByTagName("aside");
			for(let i=0; i < asides.length; i++)
				{
				asides[i].className = null;
				}
			});
		}
	}

init_viewer();

