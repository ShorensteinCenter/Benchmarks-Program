const apiForm = document.querySelector('.api-key-form');

/* Validate an API Key Submitted via the form */
const submitApiKey = async event => {
	event.preventDefault();
	apiForm.removeEventListener('submit', submitApiKey);
	disableForm(apiForm);
	if (!clientSideValidateForm(apiForm)) {
		enableForm(apiForm);
		apiForm.addEventListener('submit', submitApiKey);
		return;
	}
	const
		headers = new Headers({"X-CSRFToken": csrfToken}),
		formData = new FormData(apiForm),
		payload = {
			method: 'POST',
			credentials: 'same-origin',
			headers: headers,
			body: formData
		},
		request = new Request('/validateAPIKey', payload);
	try {
		const response = await fetch(request);
		if (response.ok) {
			keyWrapper = apiForm.querySelector('.form-input-wrapper');
			keyWrapper.classList.add('fetching', 'valid');
			getLists();
		}
		else {
			if (response.status == 400) {
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors)) {
					tagField(document.querySelector('#' + k));
				}
				enableForm(apiForm);
				apiForm.addEventListener('submit', submitApiKey);
			}
			else
				throw new Error(response.statusText);
		}
	}
	catch(e) {
		console.error(e);
	}
}

/* Fetch basic details of MailChimp lists corresponding to API Key */
const getLists = async () => {
	const
		headers = new Headers({
			"X-CSRFToken": csrfToken
		}),
		payload = {
			method: 'GET',
			credentials: 'same-origin',
			headers: headers
		},
		request = new Request('/getLists', payload);
	try {
		const response = await fetch(request);
		if (response.ok) {
			const content = await response.json();
			setupListsTable(content.lists);
		}
		else
			throw new Error(response.statusText);
	}
	catch(e) {
		console.error(e);
	}
}

apiForm.addEventListener('submit', submitApiKey);