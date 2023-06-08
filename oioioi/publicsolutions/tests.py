# ~*~ encoding: utf-8 ~*~
import re
from datetime import datetime, timezone  # pylint: disable=E0611

from django.core.cache import cache
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time, fake_timezone_now
from oioioi.contests.models import Contest, Submission
from oioioi.oi.controllers import OIContestController
from oioioi.programs.controllers import ProgrammingContestController


class TSolutionOIContestController(OIContestController):
    def can_see_publicsolutions(self, request, round):
        r_times = super(TSolutionOIContestController, self).get_round_times(
            request, round
        )
        return r_times.show_results <= request.timestamp

    def solutions_must_be_public(self, qs):
        return qs.exclude(problem_instance=4)

    def solutions_may_be_published(self, qs):
        return qs


class TSolutionSimpleContestController(ProgrammingContestController):
    def can_see_publicsolutions(self, request, round):
        r_times = super(TSolutionSimpleContestController, self).get_round_times(
            request, round
        )
        return r_times.show_results <= request.timestamp

    def solutions_must_be_public(self, qs):
        return qs.exclude(problem_instance=4)

    def solutions_may_be_published(self, qs):
        return qs


class TestPublicSolutions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
    ]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.publicsolutions.tests.TSolutionOIContestController'
        )
        contest.save()

    def _href(self, url):
        return 'href="' + url + '"'

    def _no_public_rounds(self):
        return datetime(2010, 6, 25, tzinfo=timezone.utc)

    def _rounds_14(self):
        return datetime(2013, 4, 4, tzinfo=timezone.utc)

    def _all_rounds(self):
        return datetime(2016, 1, 1, tzinfo=timezone.utc)

    def assertUserSubmissionHTMLDataCount(self, html, username, count):
        actual = len(
            re.findall((r'username.*"' + username + r'"').encode('utf-8'), html)
        )
        self.assertEqual(
            actual, count, "Expected %d html data, got %d in %s" % (count, actual, html)
        )

    def test_solutions_in_menu(self):
        contest = Contest.objects.get()
        dashboard_url = reverse('contest_dashboard', kwargs={'contest_id': contest.id})
        solutions_url = reverse('list_solutions', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_user'))

        with fake_time(self._no_public_rounds()):
            response = self.client.get(dashboard_url)
            self.assertNotContains(response, self._href(solutions_url))
            response = self.client.get(solutions_url)
            self.assertEqual(403, response.status_code)

        with fake_time(self._rounds_14()):
            response = self.client.get(dashboard_url)
            self.assertContains(response, self._href(solutions_url))
            response = self.client.get(solutions_url)
            self.assertEqual(200, response.status_code)

        self.client.logout()

    def test_public_solutions_list(self):
        contest = Contest.objects.get()
        solutions_url = reverse('list_solutions', kwargs={'contest_id': contest.id})

        def show_source_url(sub_id):
            return reverse(
                'show_submission_source',
                kwargs={'contest_id': contest.id, 'submission_id': sub_id},
            )

        def change_publication_url(way, sub_id):
            return reverse(
                'publish_solution' if way else 'unpublish_solution',
                kwargs={'contest_id': contest.id, 'submission_id': sub_id},
            )

        def check_categories_forbidden(cats, user):
            self.assertTrue(self.client.login(username=user))
            for cat in cats:
                r = self.client.get(solutions_url, {'category': cat})
                self.assertContains(r, "Select a valid choice.")
            self.client.logout()

        # Checks categories and solutions
        # pylint: disable=dangerous-default-value
        def check_visibility(good_ids, category='', users=['test_user', 'test_user2']):
            for user in users:
                self.assertTrue(self.client.login(username=user))
                r = self.client.get(solutions_url, {'category': category})
                self.assertEqual(200, r.status_code)

                for id in range(1, 5):
                    sb = Submission.objects.all().select_related().get(pk=id)
                    if id in good_ids:
                        self.assertContains(r, str(sb.problem_instance))
                        self.assertContains(r, str(sb.user.get_full_name()))
                        self.assertContains(r, self._href(show_source_url(id)))
                    else:
                        self.assertNotContains(r, self._href(show_source_url(id)))
                        if not category:
                            self.assertNotContains(r, str(sb.problem_instance))
                self.client.logout()

        def check_sources_access(good_ids, bad_ids, user):
            self.assertTrue(self.client.login(username=user))
            for id in good_ids:
                response = self.client.get(show_source_url(id))
                self.assertEqual(200, response.status_code)
            for id in bad_ids:
                response = self.client.get(show_source_url(id))
                self.assertEqual(403, response.status_code)
            self.client.logout()

        def change_publication(way, sub_id, user='test_user'):
            self.assertTrue(self.client.login(username=user))
            response = self.client.post(change_publication_url(way, sub_id))
            self.assertEqual(302, response.status_code)
            self.client.logout()

        # 'test_user' doesn't see submissions from rounds that start in future,
        # that's the way controller.filter_visible_sources works.
        with fake_time(self._no_public_rounds()):
            check_sources_access([], [1], 'test_user')

        with fake_time(self._rounds_14()):
            check_visibility([1])
            check_visibility([1], "1", users=['test_user'])

            change_publication(True, 4)
            check_visibility([1, 4])
            check_sources_access([1, 4], [], 'test_user2')

            change_publication(False, 4)
            check_visibility([1])
            check_sources_access([1], [4], 'test_user2')
            check_categories_forbidden([2, 4], 'test_user2')

        with fake_time(self._all_rounds()):
            check_visibility([1, 2, 3], users=['test_user2'])

    def test_publish_solutions(self):
        contest = Contest.objects.get()
        publish_url = reverse('publish_solutions', kwargs={'contest_id': contest.id})

        def submission_url(sub_id):
            return reverse(
                'submission', kwargs={'contest_id': contest.id, 'submission_id': sub_id}
            )

        def show_source_url(sub_id):
            return reverse(
                'show_submission_source',
                kwargs={'contest_id': contest.id, 'submission_id': sub_id},
            )

        def change_publication_url(way, sub_id):
            return reverse(
                'publish_solution' if way else 'unpublish_solution',
                kwargs={'contest_id': contest.id, 'submission_id': sub_id},
            )

        def change_publication(way, sub_id):
            r = self.client.post(change_publication_url(way, sub_id))
            self.assertEqual(302, r.status_code)

        def check_access_forbidden(sub_ids):
            for id in sub_ids:
                r = self.client.post(change_publication_url(id % 2, id))
                self.assertEqual(403, r.status_code)

        def check_visibility(good_ids, way):
            r = self.client.get(publish_url)
            self.assertEqual(200, r.status_code)
            for id in range(1, 5):
                sb = Submission.objects.get(pk=id)
                if id in good_ids:
                    self.assertContains(r, sb.get_date_display())
                    self.assertContains(r, self._href(show_source_url(id)))
                    self.assertContains(r, change_publication_url(way, id))
                    self.assertContains(r, self._href(submission_url(id)))
                else:
                    self.assertNotContains(r, sb.get_date_display())

        with fake_time(self._no_public_rounds()):
            self.assertTrue(self.client.login(username='test_user'))
            r = self.client.get(publish_url)
            self.assertEqual(403, r.status_code)
            check_access_forbidden([4])

        with fake_time(self._rounds_14()):
            check_visibility([4], True)
            change_publication(True, 4)
            check_visibility([4], False)
            check_access_forbidden([1, 2])
            self.client.logout()
            self.assertTrue(self.client.login(username='test_user2'))
            check_visibility([], True)
            check_access_forbidden([3, 4])
            self.client.logout()
            self.assertTrue(self.client.login(username='test_user'))
            change_publication(False, 4)
            check_visibility([4], True)
            self.client.logout()

    def test_ranking(self):
        def change_publication_url(way, sub_id):
            return reverse(
                'publish_solution' if way else 'unpublish_solution',
                kwargs={'contest_id': contest.id, 'submission_id': sub_id},
            )

        with fake_timezone_now(self._rounds_14()):
            contest = Contest.objects.get()
            contest.controller_name = (
                'oioioi.publicsolutions.tests.TSolutionSimpleContestController'
            )
            contest.save()

            self.assertTrue(self.client.login(username='test_user'))

            url = reverse('default_ranking', kwargs={'contest_id': contest.id})

            response = self.client.get(url)
            self.assertUserSubmissionHTMLDataCount(response.content, 'test_user', 2)

            self.assertTrue(self.client.login(username='test_user2'))
            cache.clear()
            response = self.client.get(url)
            self.assertUserSubmissionHTMLDataCount(response.content, 'test_user2', 0)

            self.assertTrue(self.client.login(username='test_user'))
            request = self.client.post(change_publication_url(True, 4))
            self.assertEqual(302, request.status_code)

            cache.clear()
            response = self.client.get(url)
            self.assertUserSubmissionHTMLDataCount(response.content, 'test_user', 2)

            self.assertTrue(self.client.login(username='test_user2'))
            cache.clear()
            response = self.client.get(url)
            self.assertUserSubmissionHTMLDataCount(response.content, 'test_user2', 0)
