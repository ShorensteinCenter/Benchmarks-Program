import pygal
from pygal import Config
from pygal.style import DefaultStyle

class Chart(object):

	Y_AXIS_MULTIPLIER = 1.33

	# The default style settings for a bart chart or histogram
	BAR_CONFIG = Config()
	BAR_CONFIG.legend_box_size = 15
	BAR_CONFIG.width = 1000
	BAR_CONFIG.legend_at_bottom = True
	BAR_CONFIG.truncate_legend = -1
	BAR_CONFIG.max_scale = 7
	BAR_CONFIG.print_values = True
	BAR_CONFIG.print_values_position = 'top'
	BAR_CONFIG.style = DefaultStyle(background='#fff', title_font_size=20)

	# Shared init stuff among all chart types
	def __init__(self, title):
		self.chart.title = title
		self.chart.range = (0, self.max_y_axis)

	# Output a chart to png
	def render_png(self, chart_name):
		self.chart.render_to_png('app/static/charts/{}.png'.format(chart_name))

class BarChart(Chart):
	def __init__(self, title, data, x_labels=None, percentage=True):
		
		# Calculate the maximum value for the y axis
		# Cannot be greater than 1 if data values are percentages
		data_list = list(val for v in data.values() for val in v)
		max_y_val = max(data_list)
		self.max_y_axis = (max_y_val * self.Y_AXIS_MULTIPLIER
			if (max_y_val * self.Y_AXIS_MULTIPLIER) <= 1 or percentage is False
			else 1)
		
		# Instantiate a pygal bar chart with relevant options
		self.chart = pygal.Bar(self.BAR_CONFIG)
		super().__init__(title)
		if x_labels is not None:
			self.chart.x_labels = x_labels
		self.add_data(data)
		self.format_values(percentage)

	# Turn decimal values into percentages with 1 decimal place
	# Turn other raw numbers into integers with comma separation
	def format_values(self, percentage):
		self.chart.value_formatter = (lambda x: 
			'{:.1%}'.format(x) if percentage else '{:,d}'.format(int(x)))

	def add_data(self, data):
		for series_name, series_data in data.items():
			self.chart.add(series_name, series_data)

class Histogram(Chart):
	def __init__(self, title, data):
		self.max_y_axis = 1
		
		# Instantiate a pygal histogram with relevant options
		self.chart = pygal.Histogram(self.BAR_CONFIG)
		super().__init__(title)
		self.add_data(data)
		self.format_values()

	# Turn axis values into percentages with 1 decimal place
	def format_values(self):
		self.chart.value_formatter = lambda x: '{:.1%}'.format(x)
		self.chart.x_value_formatter = lambda x: '{:.1%}'.format(x)

	# Add the data using a custom formatter for a histogram
	def add_data(self, data):
		for series_name, series_data in data.items():
			self.chart.add(series_name, 
				[(bin, round(start_x / 10, 1), round(start_x / 10 + .1, 1)) 
				for start_x, bin in enumerate(series_data)],
				formatter=lambda x: '{:.1%}'.format(x[0]))