# -*- coding: utf-8 -*-
from datetime import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.contrib.auth.models import User

from oioioi.base.tests import fake_time
from oioioi.contests.models import Contest
from oioioi.statistics.plotfunctions import histogram, \
                                            points_to_source_length_problem
from oioioi.contests.models import ProblemInstance
from oioioi.statistics.controllers import statistics_categories, \
                                          statistics_plot_kinds


class TestStatisticsPlotFunctions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_submission']

    def assertSizes(self, data, dims):
        """Assert that ``data`` is a ``len(dims)``-dimensional rectangular
           matrix, represented as a list, with sizes in consecutive dimensions
           as specified in ``dims``"""

        if dims == []:
            self.assertTrue(not isinstance(data, list) or data == [])
        else:
            self.assertEqual(len(data), dims[0])
            for sub in data:
                self.assertSizes(sub, dims[1:])

    def test_histogram(self):
        test1 = [0, 0, 50, 50, 100, 100]
        result1 = [[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                   [2, 0, 0, 0, 0, 2, 0, 0, 0, 0, 2]]
        self.assertEqual(histogram(test1), result1)

        test2 = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        result2 = [[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
        self.assertEqual(histogram(test2), result2)

        test3 = [34]
        result3 = [[0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33],
                   [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]]
        self.assertEqual(histogram(test3), result3)

        test4 = [0]
        result4 = [[0], [1]]
        self.assertEqual(histogram(test4), result4)

    def test_points_to_source_length(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get(short_name='zad1')
        plot = points_to_source_length_problem(pi)
        self.assertEqual(len(plot['series']), 1)
        self.assertSizes(plot['data'], [1, 1, 2])


class TestHighchartsOptions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_submission', 'test_extra_rounds']

    def test_scatter(self):
        plot_function, plot_type = \
                statistics_plot_kinds['POINTS_TO_SOURCE_LENGTH_PROBLEM']
        plot = plot_type.highcharts_options(plot_function(ProblemInstance
            .objects.filter(short_name='zad2')[0]))
        self.assertIsInstance(plot, dict)
        self.assertIn('xAxis', plot)
        self.assertIn('title', plot['xAxis'])
        self.assertIn('min', plot['xAxis'])
        self.assertIn('scatter', plot['plotOptions'])

    def test_results_histogram(self):
        plot_function, plot_type = \
                statistics_plot_kinds['POINTS_HISTOGRAM_PROBLEM']
        plot = plot_type.highcharts_options(plot_function(ProblemInstance
            .objects.filter(short_name='zad2')[0]))
        self.assertIsInstance(plot, dict)
        self.assertIn('yAxis', plot)
        self.assertIn('title', plot['yAxis'])
        self.assertIn('min', plot['yAxis'])
        self.assertIn('column', plot['plotOptions'])
        self.assertIn(';∞)', plot['xAxis']['categories'][-1])

    def test_submission_histogram(self):
        contest = Contest.objects.get()
        plot_function, plot_type = \
                statistics_plot_kinds['SUBMISSIONS_HISTOGRAM_CONTEST']
        plot = plot_type.highcharts_options(plot_function(contest))
        self.assertIsInstance(plot, dict)
        self.assertIn('yAxis', plot)
        self.assertIn('title', plot['yAxis'])
        self.assertIn('min', plot['yAxis'])
        self.assertIn('column', plot['plotOptions'])
        self.assertIn('OK', [s['name'] for s in plot['series']])


class TestStatisticsViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_submission', 'test_extra_rounds']

    def test_statistics_view(self):
        contest = Contest.objects.get()
        url = reverse('statistics_main', kwargs={'contest_id': contest.id})

        self.client.login(username='test_admin')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, 'Results histogram')

        # Ok, so now we make test_admin a regular user.
        admin = User.objects.get(username='test_admin')
        admin.is_superuser = False
        admin.save()

        self.client.login(username='test_user')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, 'Results histogram')
            self.assertContains(response, 'zad4')
            self.assertContains(response, 'zad2')
            self.assertContains(response, 'zad3')
            self.assertContains(response, 'zad1')
            self.assertContains(response,
                                "[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]")

            url = reverse('statistics_view', kwargs={'contest_id': contest.id,
                              'category': statistics_categories['PROBLEM'][1],
                              'object_name': 'zad2'})
            self.assertContains(response, url)
