const
	emailForm = document.querySelector('.email-form');

/* Perform client-side validation of the email address form */
const emailClientSideValidation = () => {
	const key = emailForm.querySelector('#key').value;
	return (key.length !== 0 && 
		key.search('@') !== -1 && key.search('.') !== -1)
}

/* Submit an email address, triggering list analysis */
const submitEmail = async event => {
	event.preventDefault();
	toggleForm(true, emailForm, submitEmail);
	if (!emailClientSideValidation()) {
		toggleForm(false, emailForm, submitEmail);
		showMsg('invalid', emailForm);
	}
	else {
		const
			headers = new Headers({
				"X-CSRFToken": csrf_token
			}),
			formData = new FormData(emailForm);
		formData.append('listId', listId);
		formData.append('memberCount', memberCount);
		formData.append('unsubscribeCount', unsubscribeCount);
		formData.append('cleanedCount', cleanedCount);
		const
			payload = {
				method: 'POST',
				credentials: 'same-origin',
				headers: headers,
				body: formData
			},
			request = new Request('/submitEmail', payload);
		try {
			const response = await fetch(request);
			if (response.ok)
				slideLeft('-300vw');
			else
				throw new Error(response.statusText);
		}
		catch(e) {
			toggleForm(false, emailForm, submitEmail);
			showMsg('invalid', emailForm);
			console.error('Failed to fetch:', e);
		}
	}
}

emailForm.addEventListener('submit', submitEmail);