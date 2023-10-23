function popup(event)
	{
	event.preventDefault();
	event.stopPropagation();
	let id = event.target.getAttribute("href").substring(1);
	let aside = document.getElementById(id).parentElement;
	console.log("aside:", aside);
	aside.className = "viewer-popup";
	aside.style.top = event.target.offsetTop + "px";
	}

function init_viewer()
	{
	let links = document.getElementsByClassName("bodyTxt")[0].getElementsByTagName("a");
	for(let i=0; i < links.length; i++)
		{
		let link = links[i];
		if(link.getAttribute("epub:type") == "noteref")
			{
			console.log(link);
			link.addEventListener("click", popup);
			}
		}

	document.addEventListener("click", function(event) {
		let asides = document.getElementsByClassName("groupExt")[0].getElementsByTagName("aside");
		for(let i=0; i < asides.length; i++)
			{
			asides[i].className = null;
			}
		});
	}

init_viewer();

