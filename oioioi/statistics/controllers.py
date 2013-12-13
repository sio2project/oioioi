from oioioi.contests.controllers import ContestController
from oioioi.base.fields import EnumRegistry
from django.utils.translation import ugettext_lazy as _


statistics_categories = EnumRegistry()
statistics_categories.register('CONTEST', _("Contest"))
statistics_categories.register('PROBLEM', _("Problem"))

statistics_plot_kinds = EnumRegistry()

class StatisticsMixinForContestController(object):
    """The basic unit of statistics module is a plot group. It is a group of
       plots. A plot group is calculated for an object. The object can be a
       contest or a problem.

       Example plot groups are:

       1. Contest -- Data is calculated for a whole contest.
       1. Problem XYZ -- Data is calculated for a XYZ problem.

       A cluster of plot groups for a certain type of object is a category.

       A plot group is represented by a category identifier and an object
       name. The name is identifying an object for which statistics will be
       calculated. The type of the object depends on the category. It can be
       a contest or a problem. The meaning of the name also depends on
       category. For a problem it is a short name. In some cases the string
       is not necessary (for example for current contest), so an empty string
       is also possible.

       A plot is a graphical representation of some data. For example:
       a histogram of results for a contest, a pie chart of AC and WA for
       a problem, a table with lengths of the shortest solutions for problems
       or even some text with the total number of submissions.

       Plot kind tells what information we want to get. For example:
       a distribution of points for a problem, length of the shortest solution
       for a problem, numbers of solution for each problem in a contest. It
       also defines the type of object for which data will be calculated.

       Example plot kinds for a problem:

       1. Number of submissions.
       1. Histogram of points.
       1. Structure of results -- how many AC, WA or TLE were reported.

       Example plot kinds for a contest:

       1. Number of accepted solutions.
       1. Time of the first AC for every problem.
       1. Number of accepted solutions for each problem.
       1. Size of the shortest solution for each problem.
       1. Structure of the results -- how many AC, WA or TLE were reported.

       Plot data is a portion of information sufficient to render a plot.
       To get plot data we need two pieces of information. One is the desired
       kind of plot. The other is the name of the object. The meaning of the
       name depends on the object type. For problem, the name is short_name.

       .. _plot-data-representation:
       Plot data is represented as a dict containing several entries:

       1. ``plot_name`` -- Title of the plot.
       1. ``plot_type`` -- An object of
          :class:`~oioioi.statistics.plottypes.PlotType`. It determines a way
          to render data. For example a histogram, plain text or x-y plot.

       Additional dict entries depend on ``plot_type``. Look at
       :class:`~oioioi.statistics.plottypes.PlotType` implementations.

       Plot kind is represented as a pair of an enum entry and a string.
    """

    def statistics_available_plot_groups(self, request):
        """Returns a list of available plot groups.

           Each entry of output describes a plot group. It contains
           a category identifier, an object name and a description of plot
           group. The description should be translated.

           :rtype: List of pairs ``(enum entry from statistics_categories,
              string, unicode)``
        """
        raise NotImplementedError

    def statistics_available_plots(self, request, plot_group):
        """Returns a list of available plots for the plot group.
           Determines which plots the requesting user is allowed to see.

           Each entry of the output contains a  plot kind identifier, an object
           name and a description. The description should be translated.

           :type plot_group: (enum entry from statistics_categories, string)
           :rtype: list of (enum entry from statistics_plot_kinds, string,
              unicode)
        """
        raise NotImplementedError

    def statistics_data(self, request, plot_kind):
        """Returns data needed to render statistics for the ``plot_kind``.

           :param plot_kind: A pair (enum entry, string).
           :return: A dict describing plot. See
              :ref:`plot-data-representation`.
           :rtype: Dict.
        """
        raise NotImplementedError

    def render_statistics(self, request, data):
        """Renders the given plots to HTML.

           :param data: A dict describing plots, as returned
              by :meth:`statistics_data`
           :type data: Dict.
           :return: Unicode containing HTML.
        """
        raise NotImplementedError

ContestController.mix_in(StatisticsMixinForContestController)
