function init_jwstream() {

	/* Embedded video player */
	const player = document.getElementById("player");

	/* HTML form with job control buttons and clip parameters */
	const form = document.getElementById("form");

	/* Top control bar (Jog, Set Start, Set End) */
	const jog_controls = document.getElementById("jog-controls").children;
	function jog_button(index, amount)
		{
		jog_controls[index].addEventListener('click', function() {
			player.currentTime = Math.floor(player.currentTime + amount + 0.5);
			});
		}
	function time_to_str(seconds)
		{
		const hours = Math.floor(seconds / 3600);
		seconds = Math.floor(seconds % 3600);
		const minutes = Math.floor(seconds / 60);
		seconds = Math.floor(seconds % 60);
		return hours + ":" + ("0" + minutes).slice(-2) + ":" + ("0" + seconds).slice(-2);
		}
	function copy_time_button(index, target)
		{
		jog_controls[index].addEventListener('click', function()
			{
			let seconds = Math.floor(player.currentTime + 0.5);
			form.elements[target].value = time_to_str(seconds);
			});
		}
	jog_button(0, -1800);
	jog_button(1, -300);
	jog_button(2, -60);
	jog_button(3, -30);
	jog_button(4, -5);
	jog_button(5, -1);
	copy_time_button(6, "clip_start");
	copy_time_button(7, "clip_end");
	jog_button(8, 1);
	jog_button(9, 5);
	jog_button(10, 30);
	jog_button(11, 60);
	jog_button(12, 300);
	jog_button(13, 1800);

	/* Second control bar (chapters) */
	const chapter_buttons = document.getElementsByClassName("chapter-button");
	function on_chapter_button(event)
		{
		player.currentTime = this.dataset.time;	
		form.elements["clip_start"].value = time_to_str(this.dataset.time);
		form.elements["clip_end"].value = "";
		form.elements["clip_title"].value = this.innerText;
		}
	for(let i=0; i < chapter_buttons.length; i++)
		{
		chapter_buttons[i].addEventListener("click", on_chapter_button);
		}

	document.documentElement.addEventListener("turbo:submit-end", function(event) {
		console.log("turbo:submit-end", event.detail);
		form.elements["clip_start"].value = "";
		form.elements["clip_end"].value = "";
		form.elements["clip_title"].value = "";
		});

	}

