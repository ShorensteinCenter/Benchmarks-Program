const listsTable = document.querySelector('.lists-table');

/* References to event listeners attached using closures */
let listeners = [];

/* Approx. how long (in seconds) it takes to analyze a list member */
const analysisTime = 0.24;

/* Function for converting seconds to times */
const secondsToHm = d => {
	if (d == 0)
		return "N/A";
	d = Number(d);
	
	const 
		h = Math.floor(d / 3600),
		m = Math.floor(d % 3600 / 60),
		hDisplay = h > 0 ? h + (m == 0 ? 
			(h == 1 ? " hour" : " hours") : 
			(h == 1 ? " hour, " : " hours, "))  : "",
		mDisplay = m > 0 ? m + (m == 1 ? " minute" : " minutes") : "",
		hm = hDisplay + mDisplay;
	
	return hm ? "~" + hm : "<1 minute";
}

/* Fill lists table with details */
const setupListsTable = data => {
	let listsTableBody = "<tbody>";

	for (let i = 0; i < data.length; ++i) {
		listsTableBody += "<tr>";
		listsTableBody += "<td>" + data[i].name + "</td>";
		listsTableBody += "<td class='d-none d-md-table-cell'>" + 
			data[i].stats.member_count.toLocaleString() + "</td>";
		const calcTime = secondsToHm(data[i].stats.member_count  * analysisTime);
		listsTableBody += "<td class='d-none d-md-table-cell'>" + 
			calcTime + "</td>";
		if (data[i].stats.member_count > 0) {
			listsTableBody += "<td class='analyze-link-column'>" +
				"<a class='analyze-link' list-id='" + 
				data[i].id + "' list-name='" + 
				data[i].name  + "' total-count='" + 
				(data[i].stats.member_count +
				data[i].stats.unsubscribe_count +
				data[i].stats.cleaned_count) + "' open-rate='" +
				data[i].stats.open_rate + "'" + " href='#'>" +
				"<div class='analyze-link-text'>Analyze</div>" +
				"<svg class='i-chevron-right' viewBox='0 0 32 32'" +
				" width='16' height='16' fill='none' " +
				"stroke='currentcolor' stroke-linecap='round' " +
				"stroke-linejoin='round' stroke-width='3'>" +
				"<path d='M12 30 L24 16 12 2'></path></svg></a></td>";
		}
		else
			listsTableBody += "<td></td>"
		listsTableBody += "</tr>";
	}
	listsTableBody += "</tbody>";
	document.querySelector('thead')
		.insertAdjacentHTML('afterend', listsTableBody);
	
	const analyzeLinks = document.querySelectorAll('.analyze-link');
	for (let i = 0; i < analyzeLinks.length; ++i) {
		const 
			listId = analyzeLinks[i].getAttribute('list-id'),
			listName = analyzeLinks[i].getAttribute('list-name'),
			totalCount = analyzeLinks[i].getAttribute('total-count'),
			openRate = analyzeLinks[i].getAttribute('open-rate'),
			listener = analyzeList(listId, listName,
				totalCount, openRate);
		analyzeLinks[i].addEventListener('click', listener);
		listeners[i] = listener;
	}
}

/* Submit a list for processing */
const analyzeList = (listId, listName, totalCount, openRate) => {
	return async e => {
		e.preventDefault();
		const analyzeLinks = document.querySelectorAll('.analyze-link');
		for (let i = 0; i < analyzeLinks.length; ++i)
			analyzeLinks[i].removeEventListener('click', listeners[i]);
		disable(document.querySelectorAll('.lists-table'));
		const 
			headers = new Headers({
				"X-CSRFToken": csrfToken,
				"content-type": "application/json"
			}),
			requestBody = {
				"list_id": listId,
				"list_name": listName,
				"total_count": totalCount,
				"open_rate": openRate
			},
			payload = {
				method: 'POST',
				credentials: 'same-origin',
				headers: headers,
				body: JSON.stringify(requestBody)
			},
			request = new Request('/analyze-list', payload);
		try {
			const response = await fetch(request);
			if (response.ok)
				console.error('ok');
			else {
				enable(document.querySelectorAll('.lists-table'));
				for (let i = 0; i < analyzeLinks.length; ++i)
					analyzeLinks[i].addEventListener('click', listeners[i]);
				throw new Error(e.statusText);
			}
		}
		catch(e) {
			console.error(e)
		}
	}
}


/* Get data about lists from the server */
const getListData = async () => {
	const
		payload = {
			credentials: 'same-origin'
		},
		request = new Request('/get-list-data', payload);
	try {
		const response = await fetch(request);
		if (response.ok) {
			const responseData = await response.json();
			setupListsTable(responseData);
		}
		else
			throw new Error(response.statusText);
	}
	catch(e) {
		console.error(e);
	}

}

if (listsTable)
	getListData();
