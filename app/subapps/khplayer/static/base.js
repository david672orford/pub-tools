function hide_progress()
	{
	setTimeout(function() {
		let bar = document.getElementById('progress-bar');
		if(bar.children.length > 0)
			bar.removeChild(bar.children[0]);		/* green <div> */	
		let message = document.getElementById('progress-message');
		message.removeChild(message.children[0]);	/* message <div> */
		message.removeChild(message.children[0]);	/* <script> */
		}, 5000)
	}
