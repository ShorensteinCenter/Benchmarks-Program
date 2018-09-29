const basicInfoForm = document.querySelector('#basic-info-form');

/* Validate basic information submitted via form */
const submitBasicInfo = async e => {
	e.preventDefault();
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
		if (response.ok) {
			const body = await response.json();
			if (body.org == 'existing') {
				const 
					title = 'Thanks!',
					body = 'We\'ve received your details. Once our team has ' +
						'reviewed your submission, we\'ll email you with ' +
						'instructions for accessing our benchmarking tool.';
				window.location.href = '/confirmation?title=' + title +
					'&body=' + body;
			}
			window.location.href = '/org-info';
		}
		else {
			if (response.status == 400) {
				const invalidElts = basicInfoForm.querySelectorAll('.invalid');
				for (let i = 0; i < invalidElts.length; ++i)
					invalidElts[i].classList.remove('invalid');
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors))
					tagField(basicInfoForm.querySelector('#' + k));
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