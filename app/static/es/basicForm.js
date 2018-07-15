const basicInfoForm = document.querySelector('#basic-info-form');

/* Validate basic information submitted via form */
const submitBasicInfo = async event => {
	event.preventDefault();
	basicInfoForm.removeEventListener('submit', submitBasicInfo);
	disable(basicInfoForm.querySelectorAll('input'));
	if (!clientSideValidateForm(basicInfoForm)) {
		enable(basicInfoForm.querySelectorAll('input'));
		basicInfoForm.addEventListener('submit', submitBasicInfo);
		return;
	}
	const
		headers = new Headers({'X-CSRFToken': csrfToken}),
		formData = new FormData(basicInfoForm),
		payload = {
			method: 'POST',
			credentials: 'same-origin',
			headers: headers,
			body: formData
		},
		request = new Request('/validate-basic-info', payload);
	try {
		const response = await fetch(request);
		if (response.ok)
			window.location.href = '/info-validated';
		else {
			if (response.status == 400) {
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors)) {
					tagField(document.querySelector('#' + k));
				}
				enable(basicInfoForm.querySelectorAll('input'));
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

if (basicInfoForm)
	basicInfoForm.addEventListener('submit', submitBasicInfo);