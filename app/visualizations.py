"""This module contains plotly visualizations."""
import plotly.graph_objs as go
import plotly.io as pio

OPACITY = 0.7
COLORS = ['rgba(0,0,51,{})', 'rgba(94,12,35,{})', 'rgba(4,103,103,{})',
          'rgba(128,128,128,{})']
FILL_COLORS = [color.format(OPACITY) for color in COLORS]
HISTOGRAM_COLORS = ['rgba(94,12,35,{})', 'rgba(84,22,43,{})',
                    'rgba(74,32,50,{})', 'rgba(64,42,58,{})',
                    'rgba(54,52,65,{})', 'rgba(44,63,73,{})',
                    'rgba(34,73,80,{})', 'rgba(24,83,88,{})',
                    'rgba(14,93,95,{})', 'rgba(4,103,103,{})']
HISTOGRAM_FILL_COLORS = [color.format(OPACITY) for color in HISTOGRAM_COLORS]
CHART_MARGIN = 55

def write_png(data, layout, filename):
    """Writes out a visualization with the given data and layout to png."""
    fig = go.Figure(data=data, layout=layout)
    pio.write_image(
        fig, 'app/static/charts/{}.png'.format(filename), scale=2)

def draw_bar(x_vals, y_vals, diff_vals, title, filename, # pylint: disable=too-many-arguments
             percentage_values=False):
    """Creates a simple bar chart. See plot.ly/python/bar-charts.

    Args:
        x_vals: a list containing the bar x-values.
        y_vals: a list containing the bar y-values
        diff_vals difference between monthly values (for labels), if the
            previous month's data is included.
        title: the chart title.
        filename: the filename of the exported png.
        percentage_values: if true, formats y-values as percentages.
    """
    label_text = [
        '{:.1%}'.format(y_val) if percentage_values
        else '{:,d}'.format(int(y_val))
        for y_val in y_vals]
    if diff_vals:
        label_text[1] += ('<br>(' + diff_vals[0] + ')')
        label_text[3] += ('<br>(' + diff_vals[1] + ')')

    trace = go.Bar(
        x=x_vals,
        y=y_vals,
        width=[0.6 for x_val in x_vals],
        text=label_text,
        textposition='outside',
        cliponaxis=False,
        marker={'color': (
            [FILL_COLORS[0], FILL_COLORS[0], FILL_COLORS[1], FILL_COLORS[1]]
            if diff_vals
            else [FILL_COLORS[0], FILL_COLORS[1]])}
    )
    data = [trace]
    layout = go.Layout(
        title=title,
        autosize=False,
        width=600,
        height=500,
        margin={'pad': 0, 'b': CHART_MARGIN - 10, 't': CHART_MARGIN + 5},
        font={'size': 9},
        titlefont={'size': 13})
    if percentage_values:
        layout.yaxis = go.layout.YAxis(tickformat=',.0%')
    write_png(data, layout, filename)

def draw_stacked_horizontal_bar(y_vals, x_series, diff_vals, title, filename):
    """Creates a horizontal stacked bar chart.

    See plot.ly/python/bar-charts/#stacked-bar-chart and
    https://plot.ly/python/horizontal-bar-charts.

    Args:
        y_vals: a list containing the bar y-values.
        x_series: a list of tuples. Each tuple represents a data series.
            The tuple's first element is the series name; the second element
            is a list containing the series data.
        diff_vals difference between monthly values (for labels), if the
            previous month's data is included.
        title: see draw_bar().
        filename: see draw_bar().
    """
    data = []
    for series_num, series_data in enumerate(x_series):

        text = []
        for series_datum_num, series_datum in enumerate(series_data[1]):
            diff_val = (
                diff_vals.pop(0)
                if diff_vals and series_datum_num % 2 != 0
                else None)

            if series_datum < .02 and series_data[0] != 'Pending %':
                text.append('')
            elif diff_val:
                text.append('{:.1%}'.format(series_datum) +
                            '<br>(' + diff_val + ')')
            else:
                text.append('{:.1%}'.format(series_datum))

        trace = go.Bar(
            y=y_vals,
            x=series_data[1],
            name=series_data[0],
            text=text,
            textposition='auto',
            textfont={'color': '#444'
                               if series_data[0] == 'Pending %'
                               else '#fff',
                      'size': 9},
            cliponaxis=False,
            marker={'color': FILL_COLORS[series_num]},
            orientation='h')
        data.append(trace)
    layout = go.Layout(
        title=title,
        barmode='stack',
        autosize=False,
        width=1000,
        height=450,
        margin={'pad': 0, 'b': CHART_MARGIN, 't': CHART_MARGIN},
        legend={'traceorder': 'normal'},
        xaxis=go.layout.XAxis(tickformat=',.0%'),
        yaxis=go.layout.YAxis(automargin=True))
    write_png(data, layout, filename)

def draw_histogram(x_data, y_data, title, legend_img_uri, filename):
    """Creates a histogram.

    Does not use plotly's histogram functionality
    (https://plot.ly/python/histograms) as the data is already binned
    in pandas (see calc_histogram() in lists.py). Instead uses a bar
    chart with no spacing and x-axis ticks between bars.

    Args:
        x_data: a dictionary containing the x-axis title and x-data.
        y_vals: a dictionary containing the y-axis title and y-data.
        title: see draw_bar().
        legend_img_uri: the URI of the legend image.
        filename: see draw_bar().
    """
    trace = go.Bar(
        x=x_data['vals'],
        y=y_data['vals'],
        text=y_data['vals'],
        textposition='outside',
        marker={'color': HISTOGRAM_FILL_COLORS})
    data = [trace]
    layout = go.Layout(
        title=title,
        annotations=[{
            'text': 'Lower Open Rates',
            'font': {
                'size': 12
            },
            'showarrow': False,
            'xref': 'paper',
            'yref': 'paper',
            'x': .12,
            'y': -0.175,
            'xanchor': 'right',
            'yanchor': 'bottom'
        }, {
            'text': 'Higher Open Rates',
            'font': {
                'size': 12
            },
            'showarrow': False,
            'xref': 'paper',
            'yref': 'paper',
            'x': .88,
            'y': -0.175,
            'xanchor': 'left',
            'yanchor': 'bottom'
        }, {
            'text': x_data['title'],
            'font': {
                'size': 13
            },
            'showarrow': False,
            'xref': 'paper',
            'yref': 'paper',
            'x': .5,
            'y': -0.275,
            'align': 'center'
        }],
        autosize=False,
        width=1000,
        margin={'t': CHART_MARGIN, 'b': 115},
        bargap=0,
        xaxis=go.layout.XAxis(
            tickmode='linear',
            tickformat=',.0%',
            tick0=0,
            dtick=0.1,),
        yaxis=go.layout.YAxis(
            title=y_data['title'],
            automargin=True,
            ticksuffix='  ',
            tickprefix='    '),
        images=[{
            'source': legend_img_uri,
            'xref': 'paper',
            'yref': 'paper',
            'x': .5,
            'y': -0.175,
            'layer': 'above',
            'sizex': .75,
            'sizey': 1,
            'xanchor': 'center',
            'yanchor': 'bottom'
        }])
    write_png(data, layout, filename)

def draw_donuts(series_names, donuts, diff_vals, title, filename):
    """Creates two side-by-side donut charts. See plot.ly/python/pie-charts/.

    Args:
        series_names: a list containing the series names.
        donuts: a list of tuples, each containing the data for a chart.
            The first element of the tuple is the chart name; the second
            is a list of data corresponding to each series.
        diff_vals difference between monthly values (for labels), if the
            previous month's data is included.
        title: see draw_bar().
        filename: see draw_bar().
    """
    data = []

    donut_domains = (
        [[0, .19], [.27, .46], [.54, .73], [.81, 1]]
        if len(donuts) == 4
        else [[.27, .46], [.54, .73]]
    )

    donut_title_x = [.095, .365, .635, .905] if len(donuts) == 4 else [.365, .635]

    for donut_num, donut in enumerate(donuts):

        text = ['{:.1%}'.format(donut_val) for donut_val in donut[1]]
        if donut_num % 2 != 0 and diff_vals:
            text[0] += ('<br>(' + diff_vals.pop(0) + ')')

        trace = go.Pie(
            values=donut[1],
            labels=series_names,
            name=donut[0],
            text=text,
            hole=.45,
            domain={'x': donut_domains[donut_num]},
            marker={'colors': FILL_COLORS,
                    'line': {'width': 0}},
            textfont={'color': '#fff', 'size': 8.5},
            textinfo='text')
        data.append(trace)
    layout = go.Layout(
        title=title,
        autosize=False,
        width=1000,
        height=500,
        margin={'pad': 0, 'b': 0, 't': CHART_MARGIN},
        annotations=[{
            'text': donut[0],
            'font': {
                'size': 12.5,
            },
            'showarrow': False,
            'align': 'center',
            'x': donut_title_x[donut_num],
            'y': .83,
            'xanchor': 'center',
            'yanchor': 'top'} for donut_num, donut in enumerate(donuts)],
        legend={'orientation': 'h',
                'xanchor': 'center',
                'yanchor': 'bottom',
                'y': .15,
                'x': .5})
    write_png(data, layout, filename)
