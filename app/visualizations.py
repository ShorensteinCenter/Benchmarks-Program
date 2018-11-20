"""This module contains plotly visualizations."""
import plotly.graph_objs as go
import plotly.io as pio

OPACITY = 0.7
COLORS = ['rgba(0,0,51,{})', 'rgba(94,12,35,{})', 'rgba(4,103,103,{})',
          'rgba(128,128,128,{})']
FILL_COLORS = [color.format(OPACITY) for color in COLORS]

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
        font={'size': 8},
        titlefont={'size': 12})
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

def draw_histogram(x_vals, y_vals, x_title, y_title, title, subtitle, filename):
    """Creates a histogram.

    Does not use plotly's histogram functionality
    (https://plot.ly/python/histograms) as the data is already binned
    in pandas (see calc_histogram() in lists.py). Instead uses a bar
    chart with no spacing and x-axis ticks between bars.

    Args:
        x_vals: a list or numpy array containing the bar x-values.
        y_vals: a list containing the histogram bins.
        x_title: the x-axis title.
        y_title: the y-axis title.
        title: see draw_bar().
        subtitle: the chart subtitle.
        filename: see draw_bar().
    """
    trace = go.Bar(
        x=x_vals,
        y=y_vals,
        text=['{:.1%}'.format(y_val) for y_val in y_vals],
        textposition='outside',
        marker={'color': FILL_COLORS[0],
                'line': {'color': COLORS[0].format(.78), 'width': 0.5}})
    data = [trace]
    layout = go.Layout(
        title=title,
        annotations=[{
            'text': subtitle,
            'font': {
                'size': 14,
            },
            'showarrow': False,
            'align': 'center',
            'x': 0.5,
            'y': 1.125,
            'xref': 'paper',
            'yref': 'paper'
        }],
        autosize=False,
        width=1000,
        bargap=0,
        xaxis=go.layout.XAxis(title=x_title,
                              tickmode='linear',
                              tickformat=',.0%',
                              tick0=0,
                              dtick=0.1),
        yaxis=go.layout.YAxis(title=y_title,
                              tickformat=',.0%',
                              automargin=True,
                              ticksuffix='  ',
                              tickprefix='    '))
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
