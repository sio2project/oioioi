from django.template.loader import render_to_string


class PlotType(object):
    def head_libraries(self):
        """Returns a list containing paths to all CSS and JS files required to
        plot data. The paths should be relative to static folder. The list
        will be converted to HTML by controller.

        Currently supported extensions: .css, .js
        """
        return []

    def render_plot(self, request, data, plot_id):
        """Renders an instance of a plot to HTML.

        :type data: Dict
        :param data: Dict describing a plot, specific for plot type.
        :param plot_id: Unique number used to create a 'namespace' in HTML.
                        For example, Highcharts JS use an id attribute
                        to identify div containing the plot.
        """
        raise NotImplementedError


class PlainTextPlot(PlotType):
    """Uses the following keys from :param data::
    ``text`` plain text to be displayed
    """

    def render_plot(self, request, data, plot_id):
        return data['text']


class TablePlot(PlotType):
    """Uses the following keys from :param data: :

    ``keys`` list of headers
    ``series`` list of series names
    ``data`` rectantular array of data
    ``plot_name`` table name to be used as a caption
    """

    def render_plot(self, request, data, plot_id):
        return render_to_string('statistics/table.html', data)


class StaticHighchartsPlot(PlotType):
    """Base class for static (non-updating) plots using Highcharts library.
    Uses the following keys from :param data: :

    * ``series`` list of series names
    * ``data`` rectantular array of data
    * ``titles`` dictionary of axes titles
    * ``x_min``, ``y_min``, ``x_max``, ``y_max`` fixed axes bounds
    * ``series_extra_options`` list of extra options for each serie
    * ``highcharts_extra_options`` hook for adding extra Highcharts options
    """

    def head_libraries(self):
        return ['highcharts/lib/highcharts.js']

    def highcharts_options(self, data):
        """Function generating options for Highcharts chart, as specified in
        http://www.highcharts.com/docs/getting-started/how-to-set-options
        """
        series = [{'name': n, 'data': d} for n, d in zip(data['series'], data['data'])]
        if 'series_extra_options' in data:
            for d, opts in zip(series, data['series_extra_options']):
                d.update(opts)
        options = {
            'chart': {'type': None},
            'title': {'text': data['plot_name']},
            'xAxis': {},
            'yAxis': {},
            'legend': {'enabled': len(data['series']) > 1},
            'plotOptions': {},
            'series': series,
        }
        # Setting axes bounds
        for a in 'x', 'y':
            for b in 'min', 'max':
                key = '%s_%s' % (a, b)
                if key in data:
                    options['%sAxis' % a][b] = data[key]
        # Setting axes titles
        if 'titles' in data:
            for (key, title) in data['titles'].items():
                options.setdefault(key, {}).update({'title': {'text': title}})
        return options

    def render_plot(self, request, data, plot_id):
        options = self.highcharts_options(data)
        # Setting extra options
        if 'highcharts_extra_options' in data:
            options.update(data['highcharts_extra_options'])
        return render_to_string(
            'statistics/highcharts-plot.html',
            {
                'plot_name_id': data['plot_name'].replace(' ', '') + str(plot_id),
                'options': options,
            },
        )


class ColumnStaticHighchartsPlot(StaticHighchartsPlot):
    """Uses the following extra keys from :param data: :

    ``keys`` list of column names
    """

    def highcharts_options(self, data):
        options = super(ColumnStaticHighchartsPlot, self).highcharts_options(data)
        options['chart']['type'] = 'column'
        options['plotOptions']['column'] = {
            'stacking': 'normal',
            'pointPadding': 0.2,
            'borderWidth': 0,
        }
        options['xAxis']['categories'] = data['keys']
        return options


class BarPercentStaticHighchartsPlot(StaticHighchartsPlot):
    """Uses the following extra keys from :param data: :

    ``keys`` list of rows names
    """

    def highcharts_options(self, data):
        options = super(BarPercentStaticHighchartsPlot, self).highcharts_options(data)
        options['chart']['type'] = 'bar'
        options['chart']['height'] = 20 * len(data['keys']) + 120
        options['plotOptions']['series'] = {
            'stacking': 'percent',
            'pointPadding': 0.2,
            'pointWidth': 15,
            'borderWidth': 0,
        }
        options['xAxis']['categories'] = data['keys']
        return options


class XYStaticHighchartsPlot(StaticHighchartsPlot):
    def highcharts_options(self, data):
        options = super(XYStaticHighchartsPlot, self).highcharts_options(data)
        options['chart'].update({'type': 'scatter', 'zoomType': 'xy'})
        options['yAxis'].update({'allowDecimals': False})
        options['plotOptions']['scatter'] = {
            'marker': {
                'radius': 5,
                'states': {'hover': {'enabled': True, 'lineColor': 'rgb(100,100,100)'}},
            }
        }
        return options


class PointsToSourceLengthProblemPlot(XYStaticHighchartsPlot):
    def head_libraries(self):
        libs = super(PointsToSourceLengthProblemPlot, self).head_libraries()
        libs += ['statistics/functions.js']
        return libs

    def highcharts_options(self, data):
        options = super(PointsToSourceLengthProblemPlot, self).highcharts_options(data)

        options['plotOptions'].setdefault('series', {}).setdefault('point', {})
        options['plotOptions']['series']['point']['events'] = {'click': 'onPointClick'}

        options.setdefault('functions', {})
        options['functions']['onPointClick'] = 'pointsToSourceLengthOnClick(this)'

        return options
