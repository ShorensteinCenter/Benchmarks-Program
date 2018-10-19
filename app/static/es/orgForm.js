const orgForm = document.querySelector('#org-form');

/* Validate and submit organization info */
const submitOrg = async e => {
	e.preventDefault();
	orgForm.removeEventListener('submit', submitOrg);
	if (!clientSideValidateForm(orgForm)) {
		orgForm.addEventListener('submit', submitOrg);
		return;
	}
	const formElts = orgForm.querySelectorAll(
		'label, .custom-control-label');
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
			const body = await response.json();
			const 
				title = 'Thanks!',
				pageBody = (body.user == 'approved') ? 'You\'re all set! ' +
					'We\'ve emailed you a unique access link.' : 'We\'ve ' +
					'received your details. Once our team has reviewed your ' +
					'submission, we\'ll email you with instructions for ' +
					'accessing our benchmarking tool.',
				url = '/confirmation?title=' + title + '&body=' + pageBody;
			window.location.href = url;
		}
		else {
			if (response.status == 422) {
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

/* Disable/enable the "Other" affiliation field based on whether the
   "Other" checkbox is checked */
const toggleOtherAffField = (otherInput, otherInputWrapper) => {
	const classes = ['valid', 'invalid'];
	otherInput.classList.remove(...classes);
	otherInput.classList.toggle('disabled-elt');
	otherInputWrapper.classList.remove(...classes);
	otherInput.value = "";
}

if (orgForm) {
	orgForm.addEventListener('submit', submitOrg);
	const
		otherCheckbox = orgForm.querySelector('#other_affiliation'),
		otherInput = orgForm.querySelector('#other_affiliation_name'),
		otherInputWrapper = orgForm.querySelector(
			'#other-affiliation-name-wrapper');
	otherCheckbox.addEventListener('change', e =>
		toggleOtherAffField(otherInput, otherInputWrapper));
}
