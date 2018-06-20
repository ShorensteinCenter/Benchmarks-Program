const basicInfoForm = document.querySelector('.basic-info-form');

/* Validate basic information submitted via form */
const submitBasicInfo = async event => {
	event.preventDefault();
	basicInfoForm.removeEventListener('submit', submitBasicInfo);
	disableForm(basicInfoForm);
	if (!clientSideValidateForm(basicInfoForm)) {
		enableForm(basicInfoForm);
		basicInfoForm.addEventListener('submit', submitBasicInfo);
		return;
	}
	const
		headers = new Headers({"X-CSRFToken": csrfToken}),
		formData = new FormData(basicInfoForm),
		payload = {
			method: 'POST',
			credentials: 'same-origin',
			headers: headers,
			body: formData
		},
		request = new Request('/validateBasicInfo', payload);
	try {
		const response = await fetch(request);
		if (response.ok)
			slideLeft();
		else {
			if (response.status == 400) {
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors)) {
					tagField(document.querySelector('#' + k));
				}
				enableForm(basicInfoForm);
				basicInfoForm.addEventListener('submit', submitBasicInfo);
			}
			else
				throw new Error(response.statusText);
		}
	}
	catch(e) {
		console.error(e);
	}
}

basicInfoForm.addEventListener('submit', submitBasicInfo);