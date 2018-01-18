/* References to event listeners attached using closures */
let listeners = [];

/* Fill lists table with details */ 
const setupListsTable = response => {
	let tableHTML = "<tbody>";
	for (let i = 0; i < response.length; ++i) {
		tableHTML += "<tr>";
		tableHTML += "<td>" + response[i].name + "</td>";
		tableHTML += "<td class='d-none d-sm-table-cell'>" + 
			response[i].stats.member_count.toLocaleString() + "</td>";
		tableHTML += "<td class='d-none d-sm-table-cell'></td>";
		tableHTML += "<td class='analyze-link-column'><a class='analyze-link' list-id='" + 
			response[i].id + "' href='#'><div class='analyze-link-text'>Analyze</div>" + 
			"<svg class='i-chevron-right' viewBox='0 0 32 32' width='16' height='16' " +
			"fill='none' stroke='currentcolor' stroke-linecap='round' stroke-linejoin='round' " +
			"stroke-width='3'><path d='M12 30 L24 16 12 2'></path></svg></a></td>";
		tableHTML += "</tr>";
	}
	tableHTML += "</tbody>";
	document.querySelector('thead').insertAdjacentHTML('afterend', tableHTML);
	const analyzeLinks = document.querySelectorAll('.analyze-link');
	for (let i = 0; i < analyzeLinks.length; ++i) {
		const 
			listId = analyzeLinks[i].getAttribute('list-id'),
			listener = analyzeList(listId);
		analyzeLinks[i].addEventListener('click', listener);
		listeners[i] = listener;
	}
	slideLeft('-100vw');
}

/* Fetch and process a list */
const analyzeList = id => {
	return async e => {
		e.preventDefault();
		const analyzeLinks = document.querySelectorAll('.analyze-link');
		for (let i = 0; i < analyzeLinks.length; ++i)
			analyzeLinks[i].removeEventListener('click', listeners[i]);
		const
			headers = new Headers({
				"X-CSRFToken": csrf_token
			}),
			payload = {
				method: 'GET',
				credentials: 'same-origin',
				headers: headers,
			},
			request = new Request('/analyzeList?id=' + id, payload);
		try {
			const response = await fetch(request);
			if (response.ok) {
				console.log('ok');
			}
			else
				throw new Error(response.statusText);
		}
		catch(e) {
			console.log('Failed to fetch:', e);
		}

	}
}