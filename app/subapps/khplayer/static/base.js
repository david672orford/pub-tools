function hide_progress()
	{
	let this_script = document.currentScript;
	setTimeout(function() {

		/* Remove the <div> which grows wider as progress is made */
		let bar = document.getElementById('progress-bar');
		while(bar.firstChild)
			bar.removeChild(bar.firstChild);

		/* Remove the <div>'s with progress messages and the <script> tag
		   which installed this timer callback, but only if that <script>
		   tag is still the last one, that is if no messages have been
		   added since. */
		let message = document.getElementById('progress-message');
		if(message.lastChild == this_script) {
			while(message.firstChild)
				message.removeChild(message.firstChild);
		}

		/* Do this five seconds from now */
		}, 5000)
	}

/* CEF in OBS 3.1.x does not implement :has() */
function css_has_polyfill() {
	let progress = document.getElementById("progress");
	let messages = document.getElementById("progress-message");
	let observer = new MutationObserver((mutationList) => {
		progress.style.visibility = messages.children.length > 0 ? "visible" : "hidden";
		});
	observer.observe(messages, {childList: true});
	}

function obsstudio_hacks(scale) {
	if("obsstudio" in window) {
		/* TODO: provide the scale in a CSS variable instead and use calc() in base.css */
		if(!document.getElementById("obs-fixes")) {
			const style = document.createElement("style");
			style.id = "obs-fixes";
			style.type = "text/css"
			style.appendChild(document.createTextNode(`
				HTML { font-family: "Open Sans", sans-serif, sans-serif; font-size: ${12 * scale}pt; }
				DIV.thumbnail { width: ${96 * scale + 2}px; height: ${54 * scale + 2}px; } 
				DIV.thumbnail.large { width: ${192 * scale + 2}px; height: ${108 * scale + 2}px; }
				.bounds BUTTON svg { width: ${64 * scale}px; height: ${36 * scale}px; }
				`));
			document.head.appendChild(style);
		}

		/*window.oncontextmenu = function(e) {
			e.preventDefault();
			alert("right click disabled");
		};*/
	}
}
