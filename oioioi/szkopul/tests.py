from datetime import UTC, datetime

from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext, override_settings
from django.urls import NoReverseMatch, reverse

from oioioi.base.main_page import unregister_main_page_view
from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import Contest, ContestView, ProblemInstance, Submission
from oioioi.problems.models import Problem
from oioioi.welcomepage.views import welcome_page_view


class TestMainPageView(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
    ]

    def setUp(self):
        super().setUp()
        unregister_main_page_view(welcome_page_view)

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links(self):
        try:
            response = self.client.get("/", follow=True)
        except NoReverseMatch as e:
            self.fail(str(e))

        self.assertContains(response, "Problemset")
        self.assertContains(response, "Task archive")

        self.assertContains(response, 'href="/problemset/"')
        self.assertContains(response, 'href="/task_archive/"')

    # Regression test for SIO-2278
    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links_translation(self):
        response = self.client.get(reverse("problemset_main"), follow=True, headers={"accept-language": "en"})

        self.assertContains(response, "Problemset")
        self.assertContains(response, "Task archive")

        response = self.client.get(reverse("problemset_main"), follow=True, headers={"accept-language": "pl"})

        self.assertContains(response, "Baza zadań")
        self.assertContains(response, "Archiwum zadań")

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_anonymous_user(self):
        try:
            response = self.client.get(reverse("index"))
        except NoReverseMatch as e:
            self.fail(str(e))

        self.assertContains(response, 'class="szkopul-logo"')

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_logged_user(self):
        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get("/", follow=True)

        self.assertContains(response, "Contests")
        self.assertContains(response, "Problemset")
        self.assertContains(response, "Task archive")

        self.assertContains(response, "Latest Contests")
        self.assertContains(response, "My Submissions")

        self.assertContains(response, "Test contest")
        self.assertContains(response, "06-03")
        self.assertContains(response, "34")

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_order_in_last_submissions(self):
        # Provides some assertion that submissions will be sorted by date
        # in a descending order.

        self.assertTrue(self.client.login(username="test_user"))

        early_date = datetime.strptime("2012-06-01", "%Y-%m-%d")
        mid_date = datetime.strptime("2012-06-02", "%Y-%m-%d")

        test_problem = Problem.objects.get(pk=1)
        contestless_instance = test_problem.main_problem_instance

        test_user = User.objects.get(username="test_user")
        test_probleminstance = ProblemInstance.objects.get(pk=1)
        Submission(problem_instance=test_probleminstance, user=test_user, date=early_date).save()

        Submission(
            problem_instance=contestless_instance,
            problem_instance_id=contestless_instance.id,
            user=test_user,
            date=mid_date,
        ).save()

        response = self.client.get("/", follow=True)

        # Cut off part of the response that is above submission table because
        # it can provide irrelevant noise.
        content = response.content.decode("utf-8")
        table_content = content[content.index("My Submissions") :]

        self.assertIn("06-01", table_content)
        self.assertIn("06-02", table_content)
        self.assertIn("06-03", table_content)

        test_early_index = table_content.index("06-01")
        test_mid_index = table_content.index("06-02")
        test_late_index = table_content.index("06-03")

        self.assertEqual(test_late_index < test_mid_index, True)
        self.assertEqual(test_mid_index < test_early_index, True)

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_user_no_submissions(self):
        self.assertTrue(self.client.login(username="test_user2"))
        response = self.client.get("/", follow=True)

        self.assertContains(response, "You haven't submitted anything yet. Try entering a contest!")


@override_settings(CONTEST_MODE=ContestMode.neutral, NUM_RECENT_CONTESTS=7)
class TestMainPageLatestContests(TestCase):
    fixtures = ["test_users", "test_contest"]

    def setUp(self):
        super().setUp()
        unregister_main_page_view(welcome_page_view)
        for i in range(9):
            Contest.objects.create(id=f"new{i}", name=f"New contest {i}", controller_name="oioioi.programs.controllers.ProgrammingContestController")
            # creation_date is auto_now_add, so it can only be set by an update.
            Contest.objects.filter(id=f"new{i}").update(creation_date=datetime(2020, 1, i + 1, tzinfo=UTC))

    def _contest_ids(self, response):
        return [contest.id for contest in response.context["contests"]]

    def test_newest_contests_first(self):
        response = self.client.get("/", follow=True)
        self.assertEqual(self._contest_ids(response), [f"new{i}" for i in range(8, 1, -1)])

    def test_recent_contests_before_newest(self):
        self.assertTrue(self.client.login(username="test_user"))
        ContestView.objects.create(user=User.objects.get(username="test_user"), contest_id="c")
        response = self.client.get("/", follow=True)
        self.assertEqual(self._contest_ids(response), ["c"] + [f"new{i}" for i in range(8, 2, -1)])

    def test_does_not_load_all_contests(self):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/", follow=True)
        contest_queries = [q["sql"] for q in ctx.captured_queries if 'FROM "contests_contest"' in q["sql"] and '"contests_contest"."name"' in q["sql"]]
        self.assertTrue(contest_queries)
        for sql in contest_queries:
            self.assertIn("LIMIT 7", sql)
