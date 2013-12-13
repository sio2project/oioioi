class PlotType(object):
    def head_libraries(self):
        """Returns a list containing paths to all CSS and JS files required to
           plot data. The paths should be relative to static folder. The list
           will be converted to HTML by controller.

           Currently supported extensions: .css, .js
        """
        raise NotImplementedError

    def render_plot(self, request, data):
        """Renders an instance of a plot to HTML.

           :type data: Dict
           :param data: Dict describing a plot. Look at :class:
          `~oioioi.statistics.controllers.StatisticsMixinForContestController`.
        """
        raise NotImplementedError
