#~*~ encoding: utf-8 ~*~
import re
from datetime import datetime
from django.test import TestCase
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from oioioi.oi.controllers import OIContestController
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.contests.models import Contest, Submission
from oioioi.base.tests import fake_time


class TSolutionOIContestController(OIContestController):

    def can_see_publicsolutions(self, request, round):
        r_times = super(TSolutionOIContestController, self) \
            .get_round_times(request, round)
        return r_times.show_results <= request.timestamp

    def solutions_must_be_public(self, qs):
        return qs.exclude(problem_instance=4)

    def solutions_may_be_published(self, qs):
        return qs


class TSolutionSimpleContestController(ProgrammingContestController):

    def can_see_publicsolutions(self, request, round):
        r_times = super(TSolutionSimpleContestController, self) \
            .get_round_times(request, round)
        return r_times.show_results <= request.timestamp

    def solutions_must_be_public(self, qs):
        return qs.exclude(problem_instance=4)

    def solutions_may_be_published(self, qs):
        return qs


class TestPublicSolutions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_extra_rounds']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
            'oioioi.publicsolutions.tests.TSolutionOIContestController'
        contest.save()

    def _href(self, url):
        return 'href="' + url + '"'

    def _no_public_rounds(self):
        return datetime(2010, 6, 25, tzinfo=utc)

    def _rounds_14(self):
        return datetime(2013, 4, 4, tzinfo=utc)

    def _all_rounds(self):
        return datetime(2016, 1, 1, tzinfo=utc)

    def assertSubmissionUrlsCount(self, string, count):
        actual = len(re.findall(r'result_url.*"/c/c/s/\d/"', string))
        self.assertEqual(actual, count)

    def assertSourceUrlsCount(self, string, count):
        actual = len(re.findall(r'result_url.*"/c/c/s/\d/source/"', string))
        self.assertEqual(actual, count)

    def test_solutions_in_menu(self):
        contest = Contest.objects.get()
        dashboard_url = reverse('contest_dashboard',
                            kwargs={'contest_id': contest.id})
        solutions_url = reverse('list_solutions',
                            kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')

        with fake_time(self._no_public_rounds()):
            response = self.client.get(dashboard_url)
            self.assertNotIn(self._href(solutions_url), response.content)
            response = self.client.get(solutions_url)
            self.assertEqual(403, response.status_code)

        with fake_time(self._rounds_14()):
            response = self.client.get(dashboard_url)
            self.assertIn(self._href(solutions_url), response.content)
            response = self.client.get(solutions_url)
            self.assertEqual(200, response.status_code)

        self.client.logout()

    def test_public_solutions_list(self):
        contest = Contest.objects.get()
        solutions_url = reverse('list_solutions',
                            kwargs={'contest_id': contest.id})

        def show_source_url(sub_id):
            return reverse('show_submission_source',
                    kwargs={'contest_id': contest.id, 'submission_id': sub_id})

        def change_publication_url(way, sub_id):
            return reverse('publish_solution' if way else 'unpublish_solution',
                    kwargs={'contest_id': contest.id, 'submission_id': sub_id})

        def check_categories_forbidden(cats, user):
            self.client.login(username=user)
            for cat in cats:
                r = self.client.get(solutions_url, {'category': cat})
                self.assertIn("Select a valid choice.", r.content)
            self.client.logout()

        # Checks categories and solutions
        # pylint: disable=dangerous-default-value
        def check_visibility(good_ids, category='',
                        users=['test_user', 'test_user2']):
            for user in users:
                self.client.login(username=user)
                r = self.client.get(solutions_url, {'category': category})
                self.assertEqual(200, r.status_code)

                for id in range(1, 5):
                    sb = Submission.objects.all().select_related().get(pk=id)
                    if id in good_ids:
                        self.assertIn(str(sb.problem_instance), r.content)
                        self.assertIn(str(sb.user.get_full_name()), r.content)
                        self.assertIn(self._href(show_source_url(id)),
                                r.content)
                    else:
                        self.assertNotIn(self._href(show_source_url(id)),
                                r.content)
                        if not category:
                            self.assertNotIn(str(sb.problem_instance),
                                    r.content)
                self.client.logout()

        def check_sources_access(good_ids, bad_ids, user):
            self.client.login(username=user)
            for id in good_ids:
                response = self.client.get(show_source_url(id))
                self.assertEqual(200, response.status_code)
            for id in bad_ids:
                response = self.client.get(show_source_url(id))
                self.assertEqual(403, response.status_code)
            self.client.logout()

        def change_publication(way, sub_id, user='test_user'):
            self.client.login(username=user)
            response = self.client.post(change_publication_url(way, sub_id))
            self.assertEqual(302, response.status_code)
            self.client.logout()

        # 'test_user' doesn't see submissions from rounds that start in future,
        # this way works controller.can_see_source
        with fake_time(self._no_public_rounds()):
            check_sources_access([], [1], 'test_user')

        with fake_time(self._rounds_14()):
            check_visibility([1])
            check_visibility([1], 1, users=['test_user'])

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
        publish_url = reverse('publish_solutions',
                        kwargs={'contest_id': contest.id})

        def submission_url(sub_id):
            return reverse('submission',
                    kwargs={'contest_id': contest.id, 'submission_id': sub_id})

        def show_source_url(sub_id):
            return reverse('show_submission_source',
                    kwargs={'contest_id': contest.id, 'submission_id': sub_id})

        def change_publication_url(way, sub_id):
            return reverse('publish_solution' if way else 'unpublish_solution',
                    kwargs={'contest_id': contest.id, 'submission_id': sub_id})

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
                    self.assertIn(sb.get_date_display(), r.content)
                    self.assertIn(self._href(show_source_url(id)), r.content)
                    self.assertIn((change_publication_url(way, id)), r.content)
                    self.assertIn(self._href(submission_url(id)), r.content)
                else:
                    self.assertNotIn(sb.get_date_display(), r.content)

        with fake_time(self._no_public_rounds()):
            self.client.login(username='test_user')
            r = self.client.get(publish_url)
            self.assertEqual(403, r.status_code)
            check_access_forbidden([4])

        with fake_time(self._rounds_14()):
            check_visibility([4], True)
            change_publication(True, 4)
            check_visibility([4], False)
            check_access_forbidden([1, 2])
            self.client.logout()
            self.client.login(username='test_user2')
            check_visibility([], True)
            check_access_forbidden([3, 4])
            self.client.logout()
            self.client.login(username='test_user')
            change_publication(False, 4)
            check_visibility([4], True)
            self.client.logout()

    def test_ranking(self):
        def change_publication_url(way, sub_id):
            return reverse('publish_solution' if way else 'unpublish_solution',
                    kwargs={'contest_id': contest.id, 'submission_id': sub_id})

        contest = Contest.objects.get()
        contest.controller_name = \
            'oioioi.publicsolutions.tests.TSolutionSimpleContestController'
        contest.save()

        self.client.login(username='test_user')

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        response = self.client.get(url)
        self.assertSubmissionUrlsCount(response.content, 2)
        self.assertSourceUrlsCount(response.content, 0)

        self.client.login(username='test_user2')
        cache.clear()
        response = self.client.get(url)
        self.assertSubmissionUrlsCount(response.content, 0)
        self.assertSourceUrlsCount(response.content, 1)

        self.client.login(username='test_user')
        request = self.client.post(change_publication_url(True, 4))
        self.assertEqual(302, request.status_code)

        cache.clear()
        response = self.client.get(url)
        self.assertSubmissionUrlsCount(response.content, 2)
        self.assertSourceUrlsCount(response.content, 0)

        self.client.login(username='test_user2')
        cache.clear()
        response = self.client.get(url)
        self.assertSubmissionUrlsCount(response.content, 0)
        self.assertSourceUrlsCount(response.content, 2)
