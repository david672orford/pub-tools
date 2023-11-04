function hide_progress()
	{
	setTimeout(function() {
		let bar = document.getElementById('progress-bar');
		while(bar.firstChild)
			bar.removeChild(bar.firstChild);
		let message = document.getElementById('progress-message');
		while(message.firstChild)
			message.removeChild(message.firstChild);
		}, 5000)
	}
