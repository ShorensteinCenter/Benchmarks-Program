"""This module deals with Pygal charts."""
import pygal
from pygal import Config
from pygal.style import DefaultStyle

# The factor to multiply the maximum y-value in the data by
# To get the height of the y-axis in the chart
Y_AXIS_MULTIPLIER = 1.33

# The default style settings for a bar chart or histogram
BAR_CONFIG = Config()
BAR_CONFIG.legend_box_size = 15
BAR_CONFIG.width = 1000
BAR_CONFIG.legend_at_bottom = True
BAR_CONFIG.truncate_legend = -1
BAR_CONFIG.max_scale = 7
BAR_CONFIG.print_values = True
BAR_CONFIG.print_values_position = 'top'
BAR_CONFIG.style = DefaultStyle(background='#fff',
                                title_font_size=20)

def render_png(chart_object, chart_name):
    """Renders the chart to png.

    Args:
        chart_object: a Pygal chart object.
        chart_name: the chart's filename.
    """
    chart_object.chart.render_to_png(
        'app/static/charts/{}.png'.format(chart_name))

class BarChart():
    """Barchart class."""
    def __init__(self, title, data, x_labels=None, percentage=True):
        """Initalizes a barchart.

        Calculates the height of the y-axis.
        Then instantiates a chart using Pygal.

        Args:
            title: the title of the chart.
            data: an ordered dict of series names and series data.
            x_labels: optional x-axis labels for each data series.
            percentage: optional boolean determining whether data
                should be formatted as a percentage.
        """

        # Calculate the maximum value for the y axis
        # Cannot be greater than 1 if data values are percentages
        data_list = list(val for v in data.values() for val in v)
        max_y_val = max(data_list)
        self.max_y_axis = (max_y_val * Y_AXIS_MULTIPLIER
                           if (max_y_val * Y_AXIS_MULTIPLIER)
                           <= 1 or percentage is False else 1)

        # Instantiate a pygal bar chart with relevant options
        self.chart = pygal.Bar(BAR_CONFIG)
        self.chart.title = title
        self.chart.range = (0, self.max_y_axis)
        if x_labels is not None:
            self.chart.x_labels = x_labels
        self.add_data(data)
        self.format_values(percentage)

    def format_values(self, percentage):
        """Formats the chart data correctly, e.g.
        number of decimal places/percentage sign/etc.

        Args:
            percentage: see init method.
        """

        # Turn decimal values into percentages with 1 decimal place
        # Turn other raw numbers into integers with comma separation
        self.chart.value_formatter = (lambda x: '{:.1%}'.format(x)
                                      if percentage else
                                      '{:,d}'.format(int(x)))

    def add_data(self, data):
        """Adds data to the chart.

        Args:
            data: see init method.
        """
        for series_name, series_data in data.items():
            self.chart.add(series_name, series_data)

class Histogram():
    """Histogram class."""
    def __init__(self, title, data):
        """Initializes a histogram.

        Sets height of y-axis to 1.
        Then instantiates a chart using Pygal.

        Args:
            title: the title of the chart.
            data: an ordered dict of series names and series data.
        """

        # Histogram bars will be percentages that add up to 100%
        self.max_y_axis = 1

        # Instantiate a pygal histogram with relevant options
        self.chart = pygal.Histogram(BAR_CONFIG)
        self.chart.title = title
        self.chart.range = (0, self.max_y_axis)
        self.add_data(data)
        self.format_values()

    def format_values(self):
        """Turns axis values into percentages with 1 decimal place."""
        self.chart.value_formatter = lambda x: '{:.1%}'.format(x) # pylint: disable=unnecessary-lambda
        self.chart.x_value_formatter = lambda x: '{:.1%}'.format(x) # pylint: disable=unnecessary-lambda

    def add_data(self, data):
        """Adds the data using a custom formatter for a histogram.

        Args:
            data: see init method.
        """
        for series_name, series_data in data.items():
            self.chart.add(series_name,
                           [(bin, round(start_x / 10, 1),
                             round(start_x / 10 + .1, 1))
                            for start_x, bin in enumerate(series_data)],
                           formatter=lambda x: '{:.1%}'.format(x[0]))
