const apiKeyForm = document.querySelector('#api-key-form');

/* Validate API Key */
const submitApiKey = async e => {
	e.preventDefault();
	apiKeyForm.removeEventListener('submit', submitApiKey);
	const formElts = apiKeyForm.querySelectorAll('select,' +
		'input:not([type="checkbox"]), .custom-control-label');
	disable(formElts);
	if (!clientSideValidateForm(apiKeyForm)) {
		enable(formElts);
		apiKeyForm.addEventListener('submit', submitApiKey);
		return;
	}
	const
		headers = new Headers({'X-CSRFToken': csrfToken}),
		formData = new FormData(apiKeyForm),
		payload = {
			method: 'POST',
			credentials: 'same-origin',
			headers: headers,
			body: formData
		},
		request = new Request('/validate-api-key', payload);
	try {
		const response = await fetch(request);
		if (response.ok)
			window.location.href = '/select-list';
		else {
			if (response.status == 400) {
				const invalidElts = apiKeyForm.querySelectorAll('.invalid');
				for (let i = 0; i < invalidElts.length; ++i)
					invalidElts[i].classList.remove('invalid');
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors)) 
					tagField(apiKeyForm.querySelector('#' + k));
				enable(formElts);
				apiKeyForm.addEventListener('submit', submitApiKey);
			}
			else
				throw new Error(response.statusText);
		}
	}
	catch(e) {
		console.error(e);
	}
}

if (apiKeyForm)
	apiKeyForm.addEventListener('submit', submitApiKey);
