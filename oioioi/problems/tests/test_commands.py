from io import StringIO

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from oioioi.base.tests import needs_linux
from oioioi.contests.models import Contest, Submission, UserResultForProblem
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagProposal,
    AlgorithmTagThrough,
    DifficultyTag,
    DifficultyTagProposal,
    DifficultyTagThrough,
    OriginInfoValue,
    OriginTag,
    Problem,
    ProblemName,
)

User = get_user_model()


@override_settings(DEBUG=True)
class TestMassCreateTool(TestCase):
    name_to_model = {
        "problems": Problem,
        "users": User,
        "algotags": AlgorithmTag,
        "difftags": DifficultyTag,
        "algothrough": AlgorithmTagThrough,
        "diffthrough": DifficultyTagThrough,
        "algoproposals": AlgorithmTagProposal,
        "diffproposals": DifficultyTagProposal,
        "contests": Contest,
        "submissions": Submission,
    }

    def _assert_model_counts(self, expected_counts, check_problem_names=True):
        auto_prefix = "_auto_"
        for name, model in self.name_to_model.items():
            # For submissions, only count those from auto-generated users
            # (the packages create submissions with model solutions).
            if name == "submissions":
                count = model.objects.filter(user__username__startswith=auto_prefix).count()
            else:
                count = model.objects.count()
            expected_count = expected_counts.get(name, 0)
            assert count == expected_count, f"Expected {expected_count} {name}, got {count}"

        # Validation for i18n problem names, can be omitted (e.g. for problems for packages).
        if check_problem_names:
            problem_amount: int = expected_counts.get("problems", Problem.objects.count())
            expected_probname_count = len(settings.LANGUAGES) * problem_amount
            probname_count = ProblemName.objects.count()
            assert probname_count == expected_probname_count, f"Expected {expected_probname_count} probnames, got {probname_count}"

    def test_long_flags_tags(self):
        out = StringIO()

        mct_args = (
            "--problems",
            "5",
            "--users",
            "5",
            "--algotags",
            "3",
            "--difftags",
            "3",
            "--algothrough",
            "5",
            "--diffthrough",
            "3",
            "--algoproposals",
            "5",
            "--diffproposals",
            "5",
        )
        call_command("mass_create_tool", *mct_args, stdout=out)
        expected_counts = {name[2:]: int(value) for name, value in zip(mct_args[::2], mct_args[1::2], strict=False)}
        self._assert_model_counts(expected_counts)

        call_command("mass_create_tool", "--wipe", stdout=out)
        self._assert_model_counts({})

    def test_max_proposals(self):
        out = StringIO()

        # As many proposals as there are unique (problem, user, tag) triples and
        # (problem, user) pairs, which is the worst case for drawing them at random.
        mct_args = (
            "--problems",
            "3",
            "--users",
            "3",
            "--algotags",
            "2",
            "--difftags",
            "2",
            "--algoproposals",
            "18",
            "--diffproposals",
            "9",
        )
        call_command("mass_create_tool", *mct_args, stdout=out)
        expected_counts = {name[2:]: int(value) for name, value in zip(mct_args[::2], mct_args[1::2], strict=False)}
        self._assert_model_counts(expected_counts)

    def _contest_test_template(self, users, submissions_per_user, submission_files=("sum-correct.cpp", "sum-various-results.cpp")):
        out = StringIO()
        call_command(
            "mass_create_tool",
            "--contestname",
            "demo",
            "--createcontest",
            "--problempackages",
            "test_full_package.tgz",
            "--users",
            str(users),
            "--submission_files",
            *submission_files,
            "--submissions_per_user",
            str(submissions_per_user),
            "--wipe",
            stdout=out,
        )
        return {
            "users": users,
            "problems": 1,
            "contests": 1,
            "submissions": users * submissions_per_user,
        }

    @needs_linux
    def test_contest_basic(self):
        expected_counts = self._contest_test_template(users=1, submissions_per_user=1, submission_files=("sum-correct.cpp",))
        self._assert_model_counts(expected_counts, check_problem_names=False)

    @pytest.mark.slow
    @needs_linux
    def test_contest_bigger(self):
        expected_counts = self._contest_test_template(users=2, submissions_per_user=3)
        self._assert_model_counts(expected_counts, check_problem_names=False)

    @override_settings(DEBUG=False)
    def test_debug_false(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "10",
                "-u",
                "10",
                "-at",
                "5",
                "-dt",
                "5",
                "-att",
                "20",
                "-dtt",
                "8",
                "-ap",
                "50",
                "-dp",
                "50",
                stdout=out,
            )

    def test_invalid_amount(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "10",
                "-u",
                "10",
                "-at",
                "5",
                "-dt",
                "-5",
                "-att",
                "20",
                "-dtt",
                "8",
                "-ap",
                "50",
                "-dp",
                "50",
                stdout=out,
            )

    def test_invalid_through_amount(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "7",
                "-at",
                "5",
                "-att",
                "40",
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "7",
                "-dt",
                "5",
                "-dtt",
                "10",
                stdout=out,
            )

    def test_invalid_proposal_amount(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "1",
                "-u",
                "1",
                "-ap",
                "1",
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "1",
                "-at",
                "1",
                "-ap",
                "1",
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-u",
                "1",
                "-at",
                "1",
                "-ap",
                "1",
                stdout=out,
            )

        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "1",
                "-u",
                "1",
                "-dp",
                "1",
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "1",
                "-dt",
                "1",
                "-dp",
                "1",
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-u",
                "1",
                "-dt",
                "1",
                "-dp",
                "1",
                stdout=out,
            )

        # More proposals than there are unique combinations to draw from.
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "2",
                "-u",
                "2",
                "-at",
                "2",
                "-ap",
                "9",
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                "mass_create_tool",
                "-p",
                "2",
                "-u",
                "2",
                "-dt",
                "2",
                "-dp",
                "5",
                stdout=out,
            )

    def test_seed_repeatability(self):
        out = StringIO()
        cmd_args = ("mass_create_tool", "-p", "3", "-u", "2", "-at", "2", "-dt", "2", "-att", "3", "-dtt", "3", "-ap", "2", "-dp", "2", "-s", "8518751")

        def _get_snapshot(extra_args=()):
            call_command(*cmd_args, *extra_args, stdout=out)
            return {name: sorted(str(obj) for obj in model.objects.all()) for name, model in self.name_to_model.items()}

        seed_snapshot = _get_snapshot()
        seed_snapshot2 = _get_snapshot(("--wipe",))
        self.assertEqual(seed_snapshot, seed_snapshot2)


class TestCreateMockCompetition(TestCase):
    fixtures = ["test_users"]

    def _create_competition(self, name, *args):
        call_command("create_mock_competition", "-n", name, *args)
        return OriginTag.objects.get(name=name).problems.all()

    def _groups_with_results(self, problems, category):
        """Values of the category (archive groups) which contain a problem with a result."""
        problems_with_results = UserResultForProblem.objects.filter(problem_instance__problem__in=problems).values_list("problem_instance__problem", flat=True)
        return set(OriginInfoValue.objects.filter(category__name=category, problems__in=problems_with_results).values_list("value", flat=True))

    def _results_snapshot(self, seed):
        """Create a competition with the seed, return its problems and results, and roll it all back.

        Running the same seed twice in one database would repeat the problem site keys.
        """
        with transaction.atomic():
            problems = self._create_competition("mock", "-b", "3", "-l", "2", "-s", str(seed), "--with-instances", "--results-for", "test_user")
            snapshot = sorted(
                (problem.names.get().name, result.score.to_int() if result else None)
                for problem in problems
                for result in [UserResultForProblem.objects.filter(problem_instance=problem.main_problem_instance).first()]
            )
            transaction.set_rollback(True)
        return snapshot

    def test_without_flags(self):
        problems = self._create_competition("plain", "-b", "3", "-l", "2", "-s", "0")

        self.assertEqual(problems.count(), 27)
        for problem in problems:
            self.assertEqual(problem.controller_name, "")
            self.assertIsNone(problem.main_problem_instance)
        self.assertFalse(Submission.objects.exists())

    def test_with_instances(self):
        problems = self._create_competition("mock", "-b", "3", "-l", "2", "-s", "0", "--with-instances")

        self.assertEqual(problems.count(), 27)
        for problem in problems:
            self.assertEqual(problem.controller_name, "oioioi.problems.controllers.ProblemController")
            self.assertIsNotNone(problem.main_problem_instance)
            self.assertIsNone(problem.main_problem_instance.contest)
            response = self.client.get(reverse("problem_site", args=(problem.problemsite.url_key,)), follow=True)
            self.assertEqual(response.status_code, 200)
        self.assertFalse(Submission.objects.exists())
        self.assertFalse(UserResultForProblem.objects.exists())

    def test_archive_shows_all_badge_colours(self):
        self._create_competition("mock", "-b", "3", "-l", "2", "-s", "0", "--with-instances", "--results-for", "test_user")
        self.assertTrue(self.client.login(username="test_user"))

        response = self.client.get(reverse("task_archive_tag", args=("mock",)), follow=True)
        self.assertEqual(response.status_code, 200)
        for badge in ("text-bg-success", "text-bg-warning", "text-bg-danger"):
            self.assertContains(response, badge)

    def test_results_spread(self):
        """There is a result of each kind, results in at least two groups, and
        at least one problem without a result. Checked on several seeds and
        tree shapes.
        """
        # (branches, levels, category of the groups the results are spread over)
        shapes = [(2, 1, "level1"), (3, 2, "level1"), (1, 2, "level2")]
        for i, (branches, levels, category) in enumerate(shapes):
            # The guarantees must not depend on the seed. Each run needs its
            # own seed, as the seed also determines the problem site keys.
            for seed in range(10 * i, 10 * i + 5):
                with self.subTest(branches=branches, levels=levels, seed=seed):
                    name = f"mock{seed}"
                    problems = self._create_competition(
                        name, "-b", str(branches), "-l", str(levels), "-s", str(seed), "--with-instances", "--results-for", "test_user"
                    )
                    results = UserResultForProblem.objects.filter(problem_instance__problem__in=problems, user__username="test_user")

                    self.assertGreaterEqual(results.count(), 3)
                    self.assertLess(results.count(), problems.count())
                    self.assertGreaterEqual(len(self._groups_with_results(problems, category)), 2)

                    scores = [result.score.to_int() for result in results]
                    self.assertIn(100, scores)
                    self.assertIn(0, scores)
                    self.assertTrue(any(0 < score < 100 for score in scores))

    def test_results_seed_repeatability(self):
        self.assertEqual(self._results_snapshot(7), self._results_snapshot(7))
        self.assertNotEqual(self._results_snapshot(7), self._results_snapshot(8))

    def test_results_for_unknown_user(self):
        with self.assertRaises(CommandError):
            call_command("create_mock_competition", "-b", "3", "--with-instances", "--results-for", "nobody")
        self.assertFalse(OriginTag.objects.exists())

    def test_results_without_instances(self):
        with self.assertRaises(CommandError):
            call_command("create_mock_competition", "-b", "3", "--results-for", "test_user")
        self.assertFalse(OriginTag.objects.exists())

    def test_results_with_too_few_groups(self):
        for branches, levels in [(1, 1), (0, 3)]:
            with self.subTest(branches=branches, levels=levels), self.assertRaises(CommandError):
                call_command("create_mock_competition", "-b", str(branches), "-l", str(levels), "--with-instances", "--results-for", "test_user")
        self.assertFalse(OriginTag.objects.exists())
