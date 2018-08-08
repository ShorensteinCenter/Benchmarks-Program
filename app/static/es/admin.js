const toggles = document.querySelectorAll('span.switch');

const changeActivationStatus = async e => {
	const toggle = e.currentTarget;
	toggle.removeEventListener('change', changeActivationStatus);
	disable(toggle);
	const
		id = toggle.getAttribute('switch-id'),
		headers = new Headers({'X-CSRFToken': csrfToken}),
		payload = {
			method: 'GET',
			credentials: 'same-origin',
			headers: headers
		},
		request = new Request('/activate-user?user=' + id,
			payload);
	try {
		const response = await fetch(request);
		if (!response.ok)
			throw new Error(response.statusText);
		else {
			enable(toggle);
			toggle.addEventListener('change', changeActivationStatus);
		}
	}
	catch(e) {
		console.error(e);
	}
}

if (toggles) {
	for (let i = 0; i < toggles.length; ++i) {
		const toggle = toggles[i];
		toggle.addEventListener('change', changeActivationStatus);
	}
}