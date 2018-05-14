/* References to event listeners attached using closures */
let listeners = [];

/* Placeholders for storing list attributes */
let
	listId = "",
	listName = "",
	totalCount = 0,
	openRate = 0;

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
const setupListsTable = response => {
	let tableHTML = "<tbody>";
	for (let i = 0; i < response.length; ++i) {
		tableHTML += "<tr>";
		tableHTML += "<td>" + response[i].name + "</td>";
		tableHTML += "<td class='d-none d-md-table-cell'>" + 
			response[i].stats.member_count.toLocaleString() + "</td>";
		const calcTime = 
			secondsToHm(response[i].stats.member_count  * analysisTime);
		tableHTML += "<td class='d-none d-md-table-cell'>" + 
			calcTime + "</td>";
		if (response[i].stats.member_count > 0) {
			tableHTML += "<td class='analyze-link-column'>" +
				"<a class='analyze-link' list-id='" + 
				response[i].id + "' list-name='" + 
				response[i].name  + "' total-count='" + 
				(response[i].stats.member_count +
				response[i].stats.unsubscribe_count +
				response[i].stats.cleaned_count) + "' open-rate='" +
				response[i].stats.open_rate + "'" + " href='#'>" +
				"<div class='analyze-link-text'>Analyze</div>" +
				"<svg class='i-chevron-right' viewBox='0 0 32 32'" +
				" width='16' height='16' fill='none' " +
				"stroke='currentcolor' stroke-linecap='round' " +
				"stroke-linejoin='round' stroke-width='3'>" +
				"<path d='M12 30 L24 16 12 2'></path></svg></a></td>";
		}
		else
			tableHTML += "<td></td>"
		tableHTML += "</tr>";
	}
	tableHTML += "</tbody>";
	document.querySelector('thead')
		.insertAdjacentHTML('afterend', tableHTML);
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
	slideLeft('-100vw');
}

/* Selects a list for processing */
const analyzeList = (id, name, total, openPct) => {
	return e => {
		e.preventDefault();
		const analyzeLinks = document.querySelectorAll('.analyze-link');
		for (let i = 0; i < analyzeLinks.length; ++i)
			analyzeLinks[i].removeEventListener('click', listeners[i]);
		listId = id;
		listName = name;
		totalCount = total;
		openRate = openPct;
		slideLeft('-200vw');
	}
}