const orgForm = document.querySelector('#org-form');

/* Validate and submit organization info */
const submitOrg = async e => {
	e.preventDefault();
	orgForm.removeEventListener('submit', submitOrg);
	const formElts = orgForm.querySelectorAll('label, .custom-control-label');
	disable(formElts);
	const
		headers = new Headers({'X-CSRFToken': csrfToken}),
		formData = new FormData(orgForm),
		payload = {
			method: 'POST',
			credentials: 'same-origin',
			headers: headers,
			body: formData
		},
		request = new Request('/validate-org-info', payload);
	try {
		const response = await fetch(request);
		if (response.ok) {
			const 
				title = 'Thanks!',
				body = 'We\'ve received your details. Once our team has ' +
					'reviewed your submission, we\'ll email you with ' +
					'instructions for accessing our benchmarking tool.';
			window.location.href = '/confirmation?title=' + title +
				'&body=' + body;
		}
		else {
			if (response.status == 400) {
				const invalidElts = orgForm.querySelectorAll('.invalid');
				for (let i = 0; i < invalidElts.length; ++i)
					invalidElts[i].classList.remove('invalid');
				const errors = await response.json();
				for (const [k, _] of Object.entries(errors)) {
					tagField(orgForm.querySelector(
						'#' + k.replace('_', '-') + '-wrapper'));
				}
				enable(formElts);
				orgForm.addEventListener('submit', submitOrg);
			}
			else
				throw new Error(response.statusText);
		}
	}
	catch(e) {
		console.error(e);
	}
}

if (orgForm)
	orgForm.addEventListener('submit', submitOrg);
