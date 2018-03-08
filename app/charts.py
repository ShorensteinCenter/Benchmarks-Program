import pygal
from pygal.style import DefaultStyle

class Chart(object):

	Y_AXIS_MULTIPLIER = 1.33
	
	def add_data(self, data):
		for series_name, series_data in data.items():
			self.chart.add(series_name, series_data)

	def set_precision(self):
		self.chart.value_formatter = (lambda x: 
			'{:.1%}'.format(x))

	def render_png(self, chart_name):
		self.chart.render_to_png('app/static/charts/{}.png'.format(chart_name))

class BarChart(Chart):
	def __init__(self, title, data, x_labels=None):
		data_list = list(val for v in data.values() for val in v)
		max_y_val = max(data_list)
		max_y_axis = (max_y_val * self.Y_AXIS_MULTIPLIER
			if (max_y_val * self.Y_AXIS_MULTIPLIER) <= 1
			else 1)
		self.chart = pygal.Bar(title=title,
			legend_box_size=15,
			width=1000,
			legend_at_bottom=True,
			truncate_legend=-1,
			max_scale=7,
			range=(0, max_y_axis),
			print_values=True,
			print_values_position='top',
			style=DefaultStyle(
				background='#fff'))
		self.set_precision()
		if x_labels is not None:
			self.chart.x_labels = x_labels
		self.add_data(data)