import pygal
from pygal.style import DefaultStyle

class Chart(object):
	def add_data(self, data):
		for series_name, series_data in data.items():
			self.chart.add(series_name, series_data)

	def set_precision(self):
		self.chart.value_formatter = (lambda x: 
			'{:.1%}'.format(x))

	def render_png(self, chart_name):
		self.chart.render_to_png('charts/' + chart_name + '.png')

class BarChart(Chart):
	def __init__(self, title, y_range, data):
		self.chart = pygal.Bar(title=title, range=y_range,
			print_values=True, style=DefaultStyle(
				value_font_family='googlefont:Raleway',
				value_font_size=30,
				value_colors=tuple('white' for datum in data)))
		self.set_precision()
		self.add_data(data)