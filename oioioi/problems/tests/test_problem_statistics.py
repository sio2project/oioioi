from functools import cmp_to_key

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import strip_tags

from oioioi.base.tests import TestCase
from oioioi.contests.handlers import update_problem_statistics
from oioioi.contests.models import Submission
from oioioi.problems.management.commands import recalculate_statistics
from oioioi.problems.models import Problem, ProblemStatistics, UserStatistics


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemStatistics(TestCase):
    fixtures = [
        'test_users',
        'test_full_package',
        'test_contest',
        'test_problem_instance',
        'test_extra_contests',
        'test_extra_problem_instance',
        'test_submissions_for_statistics',
        'test_extra_submissions_for_statistics',
    ]

    def test_statistics_updating(self):
        Submission.objects.select_for_update().filter(id__gt=4).update(kind='IGNORED')
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # Count submissions for single user in single problem instance
        # compilation error
        update_problem_statistics({'submission_id': 1})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # 0 pts
        update_problem_statistics({'submission_id': 2})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # 42 pts
        update_problem_statistics({'submission_id': 3})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 42)

        # 100 pts
        update_problem_statistics({'submission_id': 4})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # ignore 100 pts
        submission = Submission.objects.select_for_update().get(id=4)
        submission.kind = 'IGNORED'
        submission.save()
        submission.problem_instance.problem.controller.recalculate_statistics_for_user(
            submission.user
        )
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 42)

        # unignore 100 pts
        submission = Submission.objects.select_for_update().get(id=4)
        submission.kind = 'NORMAL'
        submission.save()
        submission.problem_instance.problem.controller.recalculate_statistics_for_user(
            submission.user
        )
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # delete 100 pts
        submission = Submission.objects.select_for_update().get(id=4).delete()
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 42)

    def test_statistics_probleminstances(self):
        Submission.objects.select_for_update().filter(id__gt=8).update(kind='IGNORED')

        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # Count submissions for two users in two problem instances
        # user1 to pinstance1 100 pts
        update_problem_statistics({'submission_id': 4})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # user1 to pinstance2 100 pts
        update_problem_statistics({'submission_id': 5})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # user2 to pinstance1 0 pts
        update_problem_statistics({'submission_id': 6})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 2)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 50)

        # user2 to pinstance2 50 pts
        update_problem_statistics({'submission_id': 7})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 2)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 75)

        # user2 to pinstance1 100 pts
        update_problem_statistics({'submission_id': 8})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 2)
        self.assertTrue(ps.solved == 2)
        self.assertTrue(ps.avg_best_score == 100)

    def test_recalculate_statistics(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # Best scores for user1: 100, user2: 100, user3: 0, user4: None (CE)
        manager = recalculate_statistics.Command()
        manager.run_from_argv(['manage.py', 'recalculate_statistics'])

        # refresh_from_db() won't work because statistics were deleted
        problem = Problem.objects.get(id=1)
        ps = problem.statistics
        self.assertTrue(ps.submitted == 3)
        self.assertTrue(ps.solved == 2)
        self.assertTrue(ps.avg_best_score == 66)


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemStatisticsSpecialCases(TestCase):
    fixtures = [
        'test_users',
        'test_full_package',
        'test_contest',
        'test_problem_instance',
        'test_statistics_special_cases',
    ]

    def test_statistics_null_score(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10000})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

    def test_statistics_zero_max_score(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10004})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

    def test_statistics_weird_scores(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10002})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 50)

        update_problem_statistics({'submission_id': 10003})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

    # Check if imported submissions lacking score_report.score and
    # score_report.max_score are handled correctly.
    def test_statistics_imported(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10001})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)


@override_settings(
    PROBLEM_STATISTICS_AVAILABLE=True,
    PROBLEM_TAGS_VISIBLE=False,
)
class TestProblemStatisticsDisplay(TestCase):
    fixtures = ['test_users', 'test_statistics_display']

    problem_columns_tags_invisible = [
        'short_name',
        'name',
        'submitted',
        'solved_pc',
        'avg_best_score',
        'user_score',
    ]
    problem_columns_tags_visible = [
        'short_name',
        'name',
        'tags',
        'submitted',
        'solved_pc',
        'avg_best_score',
        'user_score',
    ]
    problem_data = [
        [u'aaa', u'Aaaa', u'7', u'14%', u'50', None],
        [u'bbb', u'Bbbb', u'8', u'25%', u'45', u'0'],
        [u'ccc', u'Cccc', u'5', u'60%', u'90', u'50'],
        [u'ddd', u'Dddd', u'6', u'66%', u'80', u'90'],
    ]

    def _get_table_contents(self, html):
        col_n = html.count('<th') - html.count('<thead>')
        row_n = html.count('<tr') - 1
        # Skip first `<tr>`
        pos = html.find('<tr') + 1
        self.assertNotEqual(pos, -1)
        rows = []
        for _ in range(row_n):
            pos = html.find('<tr', pos)
            self.assertNotEqual(pos, -1)
            rows.append([])
            for _ in range(col_n):
                pos = html.find('<td', pos)
                self.assertNotEqual(pos, -1)
                none_pos = html.find('<td/>', pos)

                if none_pos == pos:
                    rows[-1].append(None)
                    pos += len('<td/>')
                else:
                    pos2 = html.find('</td>', pos)
                    self.assertNotEqual(pos2, -1)
                    rows[-1].append(strip_tags(html[pos:pos2]).strip())
                    pos = pos2 + len('</td>')
        return rows

    @staticmethod
    def _cmp_str_with_none(key_fn):
        def _cmp(a, b):
            key_a = key_fn(a)
            key_b = key_fn(b)
            if key_a is None:
                return True
            if key_b is None:
                return False
            return key_a < key_b

        return _cmp

    def _assert_rows_sorted(self, rows, order_by=0, desc=False):
        # Nones should be treated as if they were less than zeroes
        # (i.e. listed last when desc=True and listed first otherwise).
        self.assertEqual(
            rows,
            sorted(
                rows,
                key=cmp_to_key(self._cmp_str_with_none(lambda x: x[order_by])),
                reverse=desc,
            ),
        )

    def test_statistics_problem_list(self):
        self.assertTrue(self.client.login(username='test_user'))

        url_main = reverse('problemset_main')
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)

        rows = self._get_table_contents(response.content.decode('utf-8'))
        self.assertEqual(rows, self.problem_data)

        # There are exactly four problems, one for each score class.
        for result in ['result--OK', 'result--TRIED', 'result--FAILED']:
            self.assertContains(response, result, count=1)

    def test_statistics_sorting(self):
        self.assertTrue(self.client.login(username='test_user'))

        for i, column in enumerate(self.problem_columns_tags_invisible):
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'order_by': column})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i)

            response = self.client.get(url_main, {'order_by': column, 'desc': ''})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i, desc=True)

    def test_statistics_nulls(self):
        # Make ccc have null stats
        ProblemStatistics.objects.get(problem__short_name='ccc').delete()

        # Supply user_score for a
        aaa_statistics = UserStatistics(
            problem_statistics=ProblemStatistics.objects.get(problem__short_name='aaa'),
            user=User.objects.get(username='test_user'),
        )
        aaa_statistics.best_score = 0
        aaa_statistics.has_submitted = True
        aaa_statistics.save()

        self.assertTrue(self.client.login(username='test_user'))

        for column in self.problem_columns_tags_invisible[2:]:
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'order_by': column})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self.assertEqual(rows[0], [u'ccc', u'Cccc', '0', None, None, None])

            response = self.client.get(url_main, {'order_by': column, 'desc': ''})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self.assertEqual(rows[-1], [u'ccc', u'Cccc', '0', None, None, None])

    def test_statistics_sort_nulls(self):
        ProblemStatistics.objects.get(problem__short_name='ccc').delete()

        self.assertTrue(self.client.login(username='test_user'))

        for i, column in enumerate(self.problem_columns_tags_invisible):
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'order_by': column})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i)

            response = self.client.get(url_main, {'order_by': column, 'desc': ''})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i, desc=True)

    # Check that the query and the ordering are correctly preserved in links
    @override_settings(PROBLEM_TAGS_VISIBLE=True)
    def test_statistics_sorting_with_query(self):
        self.assertTrue(self.client.login(username='test_user'))

        col_no = 4
        q = 'Bbbb'
        order = self.problem_columns_tags_visible[col_no - 1]
        url_main = reverse('problemset_main')

        response = self.client.get(
            url_main, {'q': q, 'foo': 'bar', 'order_by': order, 'desc': ''}
        )
        self.assertEqual(response.status_code, 200)

        rows = self._get_table_contents(response.content.decode('utf-8'))
        self.assertEqual(len(rows), 1)

        html = response.content.decode('utf-8')
        pos = html.find('<tr>')
        for _ in range(col_no):
            pos = html.find('<th', pos) + 1
            self.assertNotEqual(pos, -1)
        pos2 = html.find('</th>', pos)
        self.assertNotEqual(pos2, -1)
        th = html[pos:pos2]
        self.assertIn('q=' + q, th)
        self.assertIn('foo=bar', th)
        # The current column link should be to reverse ordering
        self.assertNotIn('desc', th)

        pos = html.find('<th', pos) + 1
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</th>', pos)
        self.assertNotEqual(pos2, -1)
        th = html[pos:pos2]
        self.assertIn('q=' + q, th)
        self.assertIn('foo=bar', th)
        # Any other column links should be to (default) descending ordering
        self.assertIn('desc', th)
