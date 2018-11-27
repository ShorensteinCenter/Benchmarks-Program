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

def write_png(data, layout, filename):
    """Writes out a visualization with the given data and layout to png."""
    fig = go.Figure(data=data, layout=layout)
    pio.write_image(
        fig, 'app/static/charts/{}.png'.format(filename), scale=2)

def draw_bar(x_vals, y_vals, title, filename, percentage_values=False):
    """Creates a simple bar chart. See plot.ly/python/bar-charts.

    Args:
        x_vals: a list containing the bar x-values.
        y_vals: a list containing the bar y-values.
        title: the chart title.
        filename: the filename of the exported png.
        percentage_values: if true, formats y-values as percentages.
    """
    trace = go.Bar(
        x=x_vals,
        y=y_vals,
        width=[0.6 for x_val in x_vals],
        text=['{:.1%}'.format(y_val) if percentage_values
              else '{:,d}'.format(int(y_val))
              for y_val in y_vals],
        textposition='outside',
        marker={'color': FILL_COLORS[0:len(x_vals)]})
    data = [trace]
    layout = go.Layout(
        title=title,
        autosize=False,
        width=600,
        font={'size': 9},
        titlefont={'size': 13})
    if percentage_values:
        layout.yaxis = go.layout.YAxis(tickformat=',.0%')
    write_png(data, layout, filename)

def draw_stacked_horizontal_bar(y_vals, x_series, title, filename):
    """Creates a horizontal stacked bar chart.

    See plot.ly/python/bar-charts/#stacked-bar-chart and
    https://plot.ly/python/horizontal-bar-charts.

    Args:
        y_vals: a list containing the bar y-values.
        x_series: a list of tuples. Each tuple represents a data series.
            The tuple's first element is the series name; the second element
            is a list containing the series data.
        title: see draw_bar().
        filename: see draw_bar().
    """
    data = []
    for series_num, series_data in enumerate(x_series):
        trace = go.Bar(
            y=y_vals,
            x=series_data[1],
            name=series_data[0],
            text=['{:.1%}'.format(series_datum)
                  for series_datum in series_data[1]],
            textposition='auto',
            textfont={'color': '#444'
                               if series_data[0] == 'Pending %'
                               else '#fff'},
            marker={'color': FILL_COLORS[series_num]},
            orientation='h')
        data.append(trace)
    layout = go.Layout(
        title=title,
        barmode='stack',
        autosize=False,
        width=1000,
        height=450,
        xaxis=go.layout.XAxis(tickformat=',.0%'),
        yaxis=go.layout.YAxis(automargin=True,
                              ticksuffix='  '))
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
        margin={'b': 100},
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

def draw_donuts(series_names, donuts, title, filename):
    """Creates two side-by-side donut charts. See plot.ly/python/pie-charts/.

    Args:
        series_names: a list containing the series names.
        donuts: a list of tuples, each containing the data for a chart.
            The first element of the tuple is the chart name; the second
            is a list of data corresponding to each series.
        title: see draw_bar().
        filename: see draw_bar().
    """
    data = []
    for donut_num, donut in enumerate(donuts):
        trace = go.Pie(
            values=donut[1],
            labels=series_names,
            name=donut[0],
            hole=.45,
            domain={'x': [0, .46] if donut_num == 0 else [.54, 1]},
            marker={'colors': FILL_COLORS,
                    'line': {'width': 0}},
            textfont={'color': '#fff'})
        data.append(trace)
    layout = go.Layout(
        title=title,
        autosize=False,
        width=1000,
        height=550,
        annotations=[{
            'text': donut[0],
            'font': {
                'size': 14,
            },
            'showarrow': False,
            'align': 'center',
            'x': 0.18 + 0.665 * donut_num,
            'y': -0.05,
            'xref': 'paper',
            'yref': 'paper'} for donut_num, donut in enumerate(donuts)],
        legend={'y': 0.5,
                'x': 1.1})
    write_png(data, layout, filename)
