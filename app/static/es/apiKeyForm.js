const
	form = document.querySelector('.api-key-form'),
	inactiveFields = form.querySelectorAll('.api-key-submit-wrapper, #submit');
	msgFields = form.querySelectorAll('.api-key-input-wrapper, #key'),
	csrf_token = document.querySelector('meta[name=csrf-token]').content;


/* Validate an API Key Submitted via the form */
const submitApiKey = async event => {
	event.preventDefault();
	toggleForm(true);
	if (!clientSideValidation()) {
		toggleForm(false);
		showMsg('invalid');
	}
	else {
		const
			headers = new Headers({
				"X-CSRFToken": csrf_token
			}),
			formData = new FormData(form),
			payload = {
				method: 'POST',
				credentials: 'same-origin',
	            headers: headers,
	            body: formData
	        },
	 		request = new Request('/validateAPIKey', payload);
	 	try {
	 		let response = await fetch(request);
	 		if (response.ok) {
	 			showMsg('valid');
	 			getLists();
	 		}
	 		else
	 			throw new Error(response.statusText);
	 	}
	 	catch(e) {
			toggleForm(false);
			showMsg('invalid');
			console.log('Failed to fetch:', e);
	 	}
	}
}

/* Enable or Disable the API Key Form */
const toggleForm = disable => {
	if (disable) {
		form.removeEventListener('submit', submitApiKey);
		for (let i = 0; i < msgFields.length; ++i)
			msgFields[i].classList.remove('invalid');
		for (let i = 0; i < inactiveFields.length; ++i)
			inactiveFields[i].classList.add('inactive');
	}
	else {
		for (let i = 0; i < inactiveFields.length; ++i)
			inactiveFields[i].classList.remove('inactive');
		form.addEventListener('submit', submitApiKey);
	}
}

/* Perform client-side validation of the API Key Form */
const clientSideValidation = () => {
	const key = form.querySelector('#key').value;
	return (key.length !== 0 && key.search('-us') !== -1);
}

/* Show form messages */
const showMsg = msg => {
	for (let i = 0; i < msgFields.length; ++i)
		msgFields[i].classList.add(msg);
}

/* Fetch basic details of MailChimp lists corresponding to API Key */
const getLists = async () => {
	const
		headers = new Headers({
			"X-CSRFToken": csrf_token
		}),
		payload = {
			method: 'GET',
			credentials: 'same-origin',
	        headers: headers,
	    },
	 	request = new Request('/getLists', payload);
	 try {
	 	let response = await fetch(request);
	 	if (response.ok) {
	 		let content = await response.json();
	 		setupListsTable(content.lists);
	 	}
	 	else
	 		throw new Error(response.statusText);
	 }
	 catch(e) {
	 	console.log('Failed to fetch:', e);
	 }
}

/* Fill lists table with details */ 
const setupListsTable = response => {
	let tableHTML = "<tbody>";
	for (let i = 0; i < response.length; ++i) {
		tableHTML += "<tr>";
		tableHTML += "<td>" + response[i].name + "</td>";
		tableHTML += "<td>" + response[i].stats.member_count.toLocaleString() + "</td>";
		tableHTML += "<td></td>";
		tableHTML += "<td class='analyze-link-column'><a class='analyze-link' href='#'><div class='analyze-link-text'>Analyze</div><svg class='i-chevron-right' viewBox='0 0 32 32' width='16' height='16' fill='none' stroke='currentcolor' stroke-linecap='round' stroke-linejoin='round' stroke-width='3'><path d='M12 30 L24 16 12 2'></path></svg></a></td>";
		tableHTML += "</tr>";
	}
	tableHTML += "</tbody>";
	document.querySelector('thead').insertAdjacentHTML('afterend', tableHTML);
	const slides = document.querySelectorAll('.container-fluid');
	for (let i = 0; i < slides.length; ++i)
		slides[i].style.transform = 'translateX(-100vw)';
} 

form.addEventListener('submit', submitApiKey);