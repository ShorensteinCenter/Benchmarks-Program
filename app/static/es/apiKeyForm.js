const
	apiForm = document.querySelector('.api-key-form'),
	csrfToken = document.querySelector('meta[name=csrf-token]').content;

/* Validate an API Key Submitted via the form */
const submitApiKey = async event => {
	event.preventDefault();
	toggleForm(true, apiForm, submitApiKey);
	if (!apiKeyClientSideValidation()) {
		toggleForm(false, apiForm, submitApiKey);
		showMsg('invalid', apiForm);
	}
	else {
		const
			headers = new Headers({
				"X-CSRFToken": csrfToken
			}),
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
				showMsg('valid', apiForm);
				getLists();
			}
			else
				throw new Error(response.statusText);
		}
		catch(e) {
			toggleForm(false, apiForm, submitApiKey);
			showMsg('invalid', apiForm);
			console.error('Failed to fetch:', e);
		}
	}
}

/* Enable or Disable a form */
const toggleForm = (disable, formElt, listener) => {
	const 
		inactiveFields = formElt.
			querySelectorAll('.form-submit-wrapper, #submit'),
		msgFields = formElt.
			querySelectorAll('.form-input-wrapper, #key');
	if (disable) {
		formElt.removeEventListener('submit', listener);
		for (let i = 0; i < msgFields.length; ++i)
			msgFields[i].classList.remove('invalid');
		for (let i = 0; i < inactiveFields.length; ++i)
			inactiveFields[i].classList.add('inactive');
	}
	else {
		for (let i = 0; i < inactiveFields.length; ++i)
			inactiveFields[i].classList.remove('inactive');
		formElt.addEventListener('submit', listener);
	}
}

/* Perform client-side validation of the api key Form */
const apiKeyClientSideValidation = () => {
	const key = apiForm.querySelector('#key').value;
	return (key.length !== 0 && key.search('-us') !== -1);
}

/* Show form messages */
const showMsg = (msg, formElt) => {
	msgFields = formElt.
		querySelectorAll('.form-input-wrapper, #key');
	for (let i = 0; i < msgFields.length; ++i)
		msgFields[i].classList.add(msg);
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
		console.log('Failed to fetch:', e);
	}
}

/* Transition from one section of the form to the next */
const slideLeft = amt => {
	const slides = document.querySelectorAll('.container-fluid');
	for (let i = 0; i < slides.length; ++i)
		slides[i].style.transform = 'translateX(' + amt + ')';
}

apiForm.addEventListener('submit', submitApiKey);