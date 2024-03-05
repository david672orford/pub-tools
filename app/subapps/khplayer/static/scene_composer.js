function init_scene_composer() {

Array.from(document.getElementsByTagName("form")).forEach(form_el => {
	Array.from(form_el.getElementsByClassName("slider")).forEach(slider => {
		let input = slider.getElementsByTagName("input")[0];
		let span = slider.getElementsByTagName("span")[0];
		span.textContent = input.value;
		input.addEventListener("input", (event) => {
			span.textContent = event.target.value;
			post_ptz(form_el, false);
			});
		});
	Array.from(form_el.getElementsByClassName("position")).forEach(position => {
		Array.from(position.getElementsByTagName("button")).forEach(button => {
			button.addEventListener("click", (event) => {
				form_el.bounds.value = event.target.value;
				post_ptz(form_el, true);
				});
			});
		})
	});
function post_ptz(form_el, new_bounds) {
	fetch("ptz", {
		method: "POST",
		headers: {
			"Content-Type": "application/json"
			},
		body: JSON.stringify({
			scene_uuid: form_el.scene_uuid.value,
			id: parseInt(form_el.id.slice(10)), /* "sceneitem" */
			bounds: form_el.bounds.value,
			new_bounds: new_bounds,
			dimensions: form_el.dimensions.value,
			x: parseInt(form_el.x.value),
			y: parseInt(form_el.y.value),
			zoom: parseFloat(form_el.zoom.value),
			})
		});
	}

}
