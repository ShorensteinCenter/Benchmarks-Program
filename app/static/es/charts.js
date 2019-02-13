const indexBubbleChart = document.getElementById('index-bubble-chart');

/* Calculates the difference, in months, between two Date objects */
const dateDiff = pastDate => Math.floor((new Date() - pastDate) / 2592000000);

/* Updates the index page bubble chart with the current values of the list size,
    open rate, and date created field */
const updateChart = speed => {
    const
        userSubscribers = parseInt(document.getElementById('enter-list-size')
                            .value.replace(/,/g, '')),
        userOpenRate = +(document.getElementById('enter-open-rate')
                         .value.replace('%', '')),
        userListCreated = document.getElementById('enter-list-age').value;
    if (isNaN(userSubscribers) || userSubscribers < 0 || 
        isNaN(userOpenRate) || userOpenRate < 0 || userOpenRate > 100)
        return;
    const
        userListAge = dateDiff(
            new Date(new Date(userListCreated).toUTCString())),
        openRateFormatted = userOpenRate.toFixed(1),
        animation = Plotly.animate(indexBubbleChart, {
        data: [
            {x: [userListAge],
             y: [openRateFormatted],
             text: ['Age: ' + userListAge + ' months<br>' +
                    'Open Rate: ' + openRateFormatted + '%<br>' +
                    'Subscribers: ' + userSubscribers.toLocaleString()],
             marker: {
                size: [userSubscribers],
             }
            }
        ],
        traces: [1]
    }, {
        transition: {
            duration: speed,
            easing: 'ease',
        },
        frame: {
            duration: speed
        }
    });
    return animation;
}

if (indexBubbleChart) {
    const
        subscribers = JSON.parse(indexBubbleChart.getAttribute('data-subscribers')),
        openRates = JSON.parse(
            indexBubbleChart.getAttribute('data-open-rates'))
            .map(val => Math.round(1000 * val) / 10),
        listAges = JSON.parse(indexBubbleChart.getAttribute('data-ages')),
        janFirstDate = new Date(
            new Date(new Date().getFullYear() - 5, 0, 1).toUTCString());

    // Bubble chart data from the database
    const dbData = {
        x: listAges,
        y: openRates,
        text: Array.from(
            {length: listAges.length},
            (v, i) =>
                'Age: ' + listAges[i] + ' months<br>' +
                'Open Rate: ' + openRates[i] + '%<br>' +
                'Subscribers: ' + subscribers[i].toLocaleString()
        ),
        hoverinfo: 'text',
        hoverlabel: {
            bgcolor: 'rgba(167, 25, 48, .85)',
            font: {
                family: 'Montserrat, sans-serif',
                size: 12
            },

        },
        mode: 'markers',
        marker: {
            size: subscribers,
            sizeref: 2.0 * Math.max(...subscribers) / (60**2),
            sizemode: 'area',
            color: new Array(subscribers.length).fill('rgba(167, 25, 48, .85)')
        }
    };

    // Prepopulated dummy 'user' data
    const userData = {
        x: [dateDiff(janFirstDate)],
        y: [7.5],
        text: ['Age: ' + dateDiff(janFirstDate) +
               ' months<br>Open Rate: 7.5%<br>Subscribers: 5,000'],
        hoverinfo: 'text',
        hoverlabel: {
            bgcolor: 'rgba(215, 164, 45, 0.85)',
            font: {
                color: 'white',
                family: 'Montserrat, sans-serif',
                size: 12
            },
            bordercolor: 'white'
        },
        mode: 'markers',
        marker: {
            size: [5000],
            sizeref: 2.0 * Math.max(...subscribers) / (60**2),
            sizemode: 'area',
            color: ['rgba(215, 164, 45, 0.85)']
        }
    };

    const data = [dbData, userData];

    // Bubble chart visual appearance
    const layout = {
        font: {
            family: 'Montserrat, sans-serif',
            size: 16,
        },
        yaxis: {
            range: [0, (1.25 * Math.max(...openRates) > 100) ? 100 :
                        1.25 * Math.max(...openRates)],
            color: '#aaa',
            tickfont: {
                color: '#555'
            },
            tickprefix: '        ',
            ticksuffix: '%  ',
            title: 'List Open Rate',
            titlefont: {
                color: '#555'
            },
            automargin: true,
            fixedrange: true
        },
        xaxis: {
            range: [0, 1.15 * Math.max(...listAges)],
            color: '#aaa',
            tickfont: {
                color: '#555'
            },
            tickformat: ',',
            title: 'List Age (Months)',
            titlefont: {
                color: '#555'
            },
            fixedrange: true
        },
        showlegend: false,
        height: 525,
        margin: {
            t: 5,
            b: 105
        },
        hovermode: 'closest'
    };
        
    const config = {
        responsive: true,
        displayModeBar: false
    };

    Plotly.newPlot(indexBubbleChart, data, layout, config);

    // Instantiate a flatpickr date picker widget on the list age field
    flatpickr('#enter-list-age', {
        defaultDate: janFirstDate,
        maxDate: 'today',
        dateFormat: 'm/d/Y'
    });

    const enterStatsFields = document.querySelectorAll('.enter-stats input');
    for (let i = 0; i < enterStatsFields.length; ++i) {
        const elt = enterStatsFields[i];
        elt.addEventListener('change', () => updateChart(450));
    }

    /* Event listener which triggers an animation when the chart comes into view */
    const chartVisibleHandler = () => {
        const
            rect = indexBubbleChart.getBoundingClientRect(),
            top = rect.top,
            bottom = rect.bottom - 45;
        if (top >= 0 && bottom <= window.innerHeight) {
            const
                listSizeField = document.getElementById('enter-list-size'),
                openRateField = document.getElementById('enter-open-rate');
            listSizeField.value = '25,000';
            openRateField.value = '30%';
            updateChart(1500);
            document.removeEventListener('scroll', debouncedChartHandler);
        }
    }

    const debouncedChartHandler = debounced(50, chartVisibleHandler);

    document.addEventListener('scroll', debouncedChartHandler);
}