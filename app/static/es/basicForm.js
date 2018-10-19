const basicInfoForm = document.querySelector('#basic-info-form');

/* Validate basic information submitted via form */
const submitBasicInfo = async e => {
	e.preventDefault();
	basicInfoForm.removeEventListener('submit', submitBasicInfo);
	if (!clientSideValidateForm(basicInfoForm)) {
		basicInfoForm.addEventListener('submit', submitBasicInfo);
		return;
	}
	const formElts = basicInfoForm.querySelectorAll('input');
	disable(formElts);
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
		if (response.ok) {
			const body = await response.json();
			if (body.org == 'existing') {
				const
					title = 'Thanks!',
					pageBody = (body.user == 'approved') ? 'You\'re all set! ' +
						'We\'ve emailed you a unique access link.' : 'We\'ve ' +
						'received your details. Once our team has ' +
						'reviewed your submission, we\'ll email you with ' +
						'instructions for accessing our benchmarking tool.',
					url = '/confirmation?title=' + title + '&body=' + pageBody;
				window.location.href = url;
			}
			else
				window.location.href = '/org-info';
		}
		else {
			if (response.status == 422) {
				const invalidElts = basicInfoForm.querySelectorAll('.invalid');
				for (let i = 0; i < invalidElts.length; ++i)
					invalidElts[i].classList.remove('invalid');
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors))
					tagField(basicInfoForm.querySelector('#' + k));
				enable(formElts);
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