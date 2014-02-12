from django.template.loader import render_to_string


class PlotType(object):
    def head_libraries(self):
        """Returns a list containing paths to all CSS and JS files required to
           plot data. The paths should be relative to static folder. The list
           will be converted to HTML by controller.

           Currently supported extensions: .css, .js
        """
        raise NotImplementedError

    def render_plot(self, request, data, plot_id):
        """Renders an instance of a plot to HTML.

           :type data: Dict
           :param data: Dict describing a plot. Look at :class:
          `~oioioi.statistics.controllers.StatisticsMixinForContestController`.
           :param plot_id Unique number used to create a 'namespace' in HTML.
               For example, Highcharts JS use an id attribute to get the div.
        """
        raise NotImplementedError


class PlainTextPlot(PlotType):
    def head_libraries(self):
        return []

    def render_plot(self, request, data, plot_id):
        return data['text']


class HistogramPlot(PlotType):
    def head_libraries(self):
        return ['highcharts/highcharts.js']

    def render_plot(self, request, data, plot_id):
        data['plot_name_id'] = data['plot_name'].replace(' ', '') \
            + str(plot_id)
        return render_to_string('statistics/histogram.html', data)


class TablePlot(PlotType):
    def head_libraries(self):
        return []

    def render_plot(self, request, data, plot_id):
        return render_to_string('statistics/table.html', data)


class ScatterPlot(PlotType):
    def head_libraries(self):
        return ['highcharts/highcharts.js']

    def render_plot(self, request, data, plot_id):
        data['plot_name_id'] = data['plot_name'].replace(' ', '') \
            + str(plot_id)
        return render_to_string('statistics/scatter.html', data)
