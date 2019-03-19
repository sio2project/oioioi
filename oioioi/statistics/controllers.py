from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import EnumRegistry
from oioioi.contests.controllers import ContestController
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import (is_contest_admin, is_contest_observer,
                                   rounds_times, visible_problem_instances)
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.statistics.models import StatisticsConfig
from oioioi.statistics.plotfunctions import (points_histogram_contest,
                                             points_histogram_problem,
                                             points_to_source_length_problem,
                                             submissions_histogram_contest,
                                             test_scores)
from oioioi.statistics.plottypes import (BarPercentStaticHighchartsPlot,
                                         ColumnStaticHighchartsPlot,
                                         PointsToSourceLengthProblemPlot,
                                         TablePlot)

statistics_categories = EnumRegistry()
statistics_categories.register('CONTEST', (_("Contest"), 'c'))
statistics_categories.register('PROBLEM', (_("Problem"), 'p'))

statistics_plot_kinds = EnumRegistry()
statistics_plot_kinds.register('POINTS_HISTOGRAM_CONTEST',
    (points_histogram_contest, ColumnStaticHighchartsPlot()))
statistics_plot_kinds.register('SUBMISSIONS_HISTOGRAM_CONTEST',
    (submissions_histogram_contest, ColumnStaticHighchartsPlot(),))
statistics_plot_kinds.register('POINTS_HISTOGRAM_PROBLEM',
    (points_histogram_problem, ColumnStaticHighchartsPlot()))
statistics_plot_kinds.register('POINTS_TABLE_PROBLEM',
    (points_histogram_problem, TablePlot()))
statistics_plot_kinds.register('POINTS_TO_SOURCE_LENGTH_PROBLEM',
    (points_to_source_length_problem, PointsToSourceLengthProblemPlot()))
statistics_plot_kinds.register('TEST_SCORES_TABLE_PROBLEM',
    (test_scores, BarPercentStaticHighchartsPlot()))


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

           :rtype: List of tuples ``(key from statistics_categories,
              string, unicode)``
        """
        raise NotImplementedError

    def statistics_available_plots(self, request, plot_category, object_name):
        """Returns a list of available plots for the plot group.
           Determines which plots the requesting user is allowed to see.

           Each entry of the output contains a plot kind identifier and an
           object name.

           :param plot_category: A key form ``statistics_categories``.
           :rtype: list of (enum entry from statistics_plot_kinds, string)
        """
        raise NotImplementedError

    def statistics_data(self, request, plot_kind, object_name):
        """Returns data needed to render statistics for the ``plot_kind``.

           :return: A dict describing plot. See
              :ref:`plot-data-representation`.
           :rtype: Dict.
        """
        raise NotImplementedError

    def render_statistics(self, request, data, plot_id):
        """Renders the given plots to HTML.

           :param data: A dict describing plots, as returned
              by :meth:`statistics_data`
           :type data: Dict.
           :param plot_id: Look at
               :class:`~oioioi.statistics.plottypes.PlotType`.
           :return: Unicode containing HTML.
        """
        raise NotImplementedError

    def can_see_stats(self, request):
        """Determines if statistics should be shown"""
        if is_contest_admin(request) or is_contest_observer(request):
            return True
        try:
            sconfig = request.contest.statistics_config
            return sconfig.visible_to_users and \
                request.timestamp >= sconfig.visibility_date
        except StatisticsConfig.DoesNotExist:
            return False

ContestController.mix_in(StatisticsMixinForContestController)


class StatisticsMixinForProgrammingContestController(object):
    def can_see_problem_statistics(self, request, pi):
        controller = pi.controller
        rtimes = rounds_times(request, self.contest)

        can_see_problem = controller.can_see_problem(request, pi)
        if pi.round:
            can_see_round_results = rtimes[pi.round].public_results_visible(
                    request.timestamp)
        else:
            can_see_round_results = False
        can_observe = is_contest_admin(request) or is_contest_observer(request)

        return can_see_problem and (can_see_round_results or can_observe)

    def statistics_available_plot_groups(self, request):
        result = []
        contest_pis = ProblemInstance.objects.filter(contest=request.contest)

        can_see_all_problems = True
        for pi in contest_pis:
            if self.can_see_problem_statistics(request, pi):
                result.append(('PROBLEM', pi.short_name, pi))
            else:
                can_see_all_problems = False

        if can_see_all_problems and contest_pis.exists():
            result.insert(0, ('CONTEST', request.contest.id,
                              request.contest))
        return result

    def statistics_available_plots(self, request, category, object):
        """Available plots for given object in given category.
           Does not check user's permission for viewing those statistics."""

        result = []
        rtimes = rounds_times(request, self.contest)

        def plot_kind(name, object):
            return (statistics_plot_kinds[name], object)

        def pi_results_visible(pi):
            return rtimes[pi.round].public_results_visible(request.timestamp) \
                   or is_contest_admin(request) or is_contest_observer(request)

        if category == 'CONTEST':
            if not object:
                object = request.contest

            result.append(plot_kind('SUBMISSIONS_HISTOGRAM_CONTEST', object))

            pis = visible_problem_instances(request)

            # Do not add this plot if it would be empty.
            if any(pi_results_visible(pi) and not pi.round.is_trial
                   for pi in pis):
                result.append(plot_kind('POINTS_HISTOGRAM_CONTEST', object))

        if category == 'PROBLEM':
            result.append(plot_kind('POINTS_HISTOGRAM_PROBLEM', object))
            result.append(plot_kind('POINTS_TABLE_PROBLEM', object))
            result.append(plot_kind('POINTS_TO_SOURCE_LENGTH_PROBLEM', object))
            result.append(plot_kind('TEST_SCORES_TABLE_PROBLEM', object))

        return result

    def statistics_data(self, request, plot_kind, object):
        (plot_function, plot_type) = plot_kind
        result = plot_function(request, object)
        result['plot_type'] = plot_type

        return result

    def render_statistics(self, request, data, plot_id):
        return data['plot_type'].render_plot(request, data, plot_id)

ProgrammingContestController.mix_in(
    StatisticsMixinForProgrammingContestController)
