/* References to event listeners attached using closures */
let listeners = [];

/* Placeholders for storing list attributes */
let
	listId = "",
	listName = "",
	memberCount = 0,
	unsubscribeCount = 0,
	cleanedCount = 0,
	openRate = 0;

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
			response[i].id + "' list-name='" + response[i].name  +
			"' member-count='" + response[i].stats.member_count + 
			"' unsubscribe-count='" + response[i].stats.unsubscribe_count + 
			"' cleaned-count='" + response[i].stats.cleaned_count + 
			"' open-rate='" + response[i].stats.open_rate + "'" +
			" href='#'><div class='analyze-link-text'>Analyze</div>" + 
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
			listName = analyzeLinks[i].getAttribute('list-name'),
			members = analyzeLinks[i].getAttribute('member-count'),
			unsubscribes = analyzeLinks[i].getAttribute('unsubscribe-count'),
			cleans = analyzeLinks[i].getAttribute('cleaned-count');
			openRate = analyzeLinks[i].getAttribute('open-rate');
			listener = analyzeList(listId, listName,
				members, unsubscribes, cleans, openRate);
		analyzeLinks[i].addEventListener('click', listener);
		listeners[i] = listener;
	}
	slideLeft('-100vw');
}

/* Selects a list for processing */
const analyzeList = (id, name, members, unsubscribes, cleans, openPct) => {
	return e => {
		e.preventDefault();
		const analyzeLinks = document.querySelectorAll('.analyze-link');
		for (let i = 0; i < analyzeLinks.length; ++i)
			analyzeLinks[i].removeEventListener('click', listeners[i]);
		listId = id;
		listName = name;
		memberCount = members;
		unsubscribeCount = unsubscribes;
		cleanedCount = cleans;
		openRate = openPct;
		slideLeft('-200vw');
	}
}