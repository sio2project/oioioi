# coding: utf-8

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import (
    ProblemInstance,
    ScoreReport,
    Submission,
    SubmissionReport,
    UserResultForProblem,
)
from oioioi.contests.scores import IntegerScore
from oioioi.problems.models import OriginInfoCategory, OriginInfoValue, Problem
from oioioi.problems.utils import get_prefetched_value

@override_settings(LANGUAGE_CODE='pl')
class TestTaskArchive(TestCase):
    fixtures = [
        'test_task_archive',
        'test_users',
        'admin_admin',
        'test_task_archive_progress_labels',
    ]

    def test_unicode_names(self):
        ic = OriginInfoCategory.objects.get(pk=3)
        self.assertEqual(ic.full_name, u"Dzień")
        iv = OriginInfoValue.objects.get(pk=4)
        self.assertEqual(iv.full_name, u"Olimpiada Informatyczna Finał")

    def test_task_archive_main(self):
        response = self.client.get(reverse('task_archive'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Olimpiada Informatyczna')
        self.assertContains(response, 'Potyczki Algorytmiczne')

    def test_fake_origin_eq(self):
        not_fake = OriginInfoValue.objects.get(pk=4)
        problem = Problem.objects.get(pk=1)
        fake = get_prefetched_value(problem, None)
        self.assertTrue((fake == not_fake) is False)

    def test_task_archive_tag(self):
        url = reverse('task_archive_tag', args=('oi',))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Olimpiada Informatyczna')
        self.assertNotContains(response, 'Potyczki Algorytmiczne')
        self.assertContains(response, 'Edycja')
        self.assertContains(response, 'XXIV OI')
        self.assertContains(response, 'XXV OI')
        self.assertContains(response, 'Etap')
        self.assertContains(response, 'Drugi Etap')
        self.assertContains(response, 'Finał')

        self.assertNotContains(response, "alert-warning")
        html = response.content.decode('utf-8')

        pos = html.find('problemgroups')
        self.assertTrue(pos != -1)
        pos = html.find('problemgroups-xxiv', pos)
        self.assertTrue(pos != -1)
        pos = html.find('problemgroups-xxiv-s2', pos)
        self.assertTrue(pos != -1)

        pos1 = html.find('24_s2 1', pos)
        self.assertTrue(pos1 != -1)
        pos2 = html.find('24_s2 2', pos)
        self.assertTrue(pos2 != -1)

        # Test sorting by short names: "24_s2 1" < "24_s2 2"
        self.assertTrue(pos1 < pos2)

        pos = html.find('problemgroups-xxiv-s3', pos)
        self.assertTrue(pos != -1)

        pos1 = html.find('24_s3_d1', pos)
        self.assertTrue(pos1 != -1)
        pos2 = html.find('24_s3_d2', pos)
        self.assertTrue(pos2 != -1)

        # Test sorting by short names: "primary" < "secondary"
        # The short names are such that their alphabetical order does not agree
        # with the names and IDs so that the test is slightly more effective.
        self.assertTrue(pos2 < pos1)

        pos = html.find('problemgroups-xxv', pos)
        self.assertTrue(pos != -1)
        pos = html.find('problemgroups-xxv-s3', pos)
        self.assertTrue(pos != -1)

        pos = html.find('25_s3 1', pos)
        self.assertTrue(pos != -1)
        pos = html.find('25_s3_d2', pos)
        self.assertTrue(pos != -1)

        pos = html.find('</div>', pos)
        self.assertTrue(pos != -1)
        pos = html.find('25 bug', pos)
        self.assertTrue(pos != -1)

        pos = html.find('</div>', pos)
        self.assertTrue(pos != -1)
        pos = html.find('no info', pos)
        self.assertTrue(pos != -1)

        self.assertNotContains(response, 'problemgroups-xxv-s2')
        self.assertNotContains(response, '-d1')
        self.assertNotContains(response, '-d2')

    def test_task_archive_tag_filter(self):
        def assert_problem_found(filters, found=True):
            url = reverse('task_archive_tag', args=('oi',)) + filters
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Olimpiada Informatyczna')
            if found:
                self.assertContains(response, '24_s3_d2')
            else:
                self.assertNotContains(response, '24_s3_d2')

        assert_problem_found('')
        assert_problem_found('?edition=xxiv')
        assert_problem_found('?stage=s3')
        assert_problem_found('?edition=xxiv&stage=s3')

        assert_problem_found('?stage=s2', found=False)
        assert_problem_found('?stage=s2&stage=s3')
        assert_problem_found('?edition=xxv', found=False)
        assert_problem_found('?edition=xxiv&edition=xxv')
        assert_problem_found('?stage=s2&edition=xxiv&edition=xxv', found=False)
        assert_problem_found('?stage=s2&stage=s3&edition=xxv', found=False)
        assert_problem_found('?stage=s2&stage=s3&edition=xxiv&edition=xxv')

    def test_task_archive_tag_filter_no_meta_on_problem(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?day=d2'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Olimpiada Informatyczna')

        self.assertContains(response, '24_s3_d2')
        self.assertContains(response, '25_s3_d2')

        self.assertNotContains(response, '24_s2 1')
        self.assertNotContains(response, '24_s2 2')
        self.assertNotContains(response, '24_s3_d1')
        self.assertNotContains(response, '25_s3 1')
        self.assertNotContains(response, '25 bug')
        self.assertNotContains(response, 'no info')

    def test_task_archive_tag_filter_no_meta_on_problem_and_fbclick_tag(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?day=d2&fbclid=a'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Olimpiada Informatyczna')

        self.assertContains(response, '24_s3_d2')
        self.assertContains(response, '25_s3_d2')

        self.assertNotContains(response, '24_s2 1')
        self.assertNotContains(response, '24_s2 2')
        self.assertNotContains(response, '24_s3_d1')
        self.assertNotContains(response, '25_s3 1')
        self.assertNotContains(response, '25 bug')
        self.assertNotContains(response, 'no info')

    def test_task_archive_tag_filter_no_problems(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?stage=1'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Olimpiada Informatyczna')
        self.assertContains(response, "alert-warning")
        self.assertNotContains(response, 'problemgroups')
        self.assertNotContains(response, '24_')
        self.assertNotContains(response, '25_')
        self.assertNotContains(response, '25 bug')
        self.assertNotContains(response, 'no info')

    def test_task_archive_tag_invalid_filter(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?invalid=filter'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_task_archive_tag_fbredirect_filter(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?fbclid=filter'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_task_archive_progress_labels(self):
        url = reverse('task_archive_tag', args=('oi',))

        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "alert-warning")
        self.assertContains(response, "[16.7%]")
        self.assertContains(response, "%", count=1)

        html = response.content.decode('utf-8')

        pos = html.find('badge-danger')
        self.assertTrue(pos == -1)
        pos = html.find('badge-warning')
        self.assertTrue(pos == -1)
        pos = html.find('<a class="badge badge-success" href="/s/2/"> 100</a>')
        self.assertTrue(pos != -1)

        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "alert-warning")
        self.assertContains(response, "[0.0%]")
        self.assertContains(response, "[12.5%]")
        self.assertContains(response, "%", count=2)

        html = response.content.decode('utf-8')

        pos = html.find('<a class="badge badge-danger" href="/s/3/"> 0</a>')
        self.assertTrue(pos != -1)
        pos = html.find('<a class="badge badge-warning" href="/s/6/"> 50</a>')
        self.assertTrue(pos != -1)
        pos = html.find('badge-success')
        self.assertTrue(pos == -1)

        def test_can_access_with_result(score, max_score):
            user = User.objects.get(username='test_user2')
            problem_instance = ProblemInstance.objects.get(pk=4)
            submission = Submission.objects.create(
                problem_instance=problem_instance, score=score, user=user
            )
            submission_report = SubmissionReport.objects.create(
                kind='NORMAL', submission=submission
            )
            score_report = ScoreReport.objects.create(
                score=score,
                status="OK",
                max_score=max_score,
                submission_report=submission_report,
            )
            user_result = UserResultForProblem.objects.create(
                score=score,
                status='OK',
                user=user,
                submission_report=submission_report,
                problem_instance=problem_instance,
            )

            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)

            user_result.delete()
            score_report.delete()
            submission_report.delete()
            submission.delete()

        # we assume that if a max_score exists it never equals zero
        # test_can_access_with_result(IntegerScore(0), IntegerScore(0))
        test_can_access_with_result(None, None)
        test_can_access_with_result(IntegerScore(50), IntegerScore(100))
        test_can_access_with_result(None, IntegerScore(100))
        test_can_access_with_result(IntegerScore(50), None)
