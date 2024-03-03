function init_cameras() {

Array.from(document.getElementsByTagName("form")).forEach(form_el => {
	Array.from(form_el.getElementsByClassName("slider")).forEach(slider => {
		let input = slider.getElementsByTagName("input")[0];
		let span = slider.getElementsByTagName("span")[0];
		span.textContent = input.value;
		input.addEventListener("input", (event) => {
			span.textContent = event.target.value;
			post_ptz(form_el);
			});
		});
	});
function post_ptz(form_el) {
	fetch("ptz", {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
			},
		body: JSON.stringify({
			scene_uuid: form_el.scene_uuid.value,
			id: parseInt(form_el.id.slice(6)),
			width: parseInt(form_el.width.value),
			height: parseInt(form_el.height.value),
			x: parseInt(form_el.x.value),
			y: parseInt(form_el.y.value),
			zoom: parseFloat(form_el.zoom.value),
			})
		});
	}

}
