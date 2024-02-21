function hide_progress()
	{
	setTimeout(function() {

		/* Remove the <div> which grows wider as progress is made */
		let bar = document.getElementById('progress-bar');
		while(bar.firstChild)
			bar.removeChild(bar.firstChild);

		/* Remove the <div>'s with progress messages and the <script> tag which called this function */
		let message = document.getElementById('progress-message');
		while(message.firstChild)
			message.removeChild(message.firstChild);

		/* Do this five seconds from now */
		}, 5000)
	}
