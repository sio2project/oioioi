from io import StringIO

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from oioioi.contests.models import Contest, Submission
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagProposal,
    AlgorithmTagThrough,
    DifficultyTag,
    DifficultyTagProposal,
    DifficultyTagThrough,
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
            "10",
            "--users",
            "10",
            "--algotags",
            "5",
            "--difftags",
            "5",
            "--algothrough",
            "20",
            "--diffthrough",
            "8",
            "--algoproposals",
            "50",
            "--diffproposals",
            "50",
        )
        call_command("mass_create_tool", *mct_args, stdout=out)
        expected_counts = {
            name[2:]: int(value)
            for name, value in zip(mct_args[::2], mct_args[1::2])
        }
        self._assert_model_counts(expected_counts)

        call_command("mass_create_tool", "--wipe", stdout=out)
        self._assert_model_counts({})

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

    def test_contest_basic(self):
        expected_counts = self._contest_test_template(users=1, submissions_per_user=1, submission_files=("sum-correct.cpp",))
        self._assert_model_counts(expected_counts, check_problem_names=False)

    @pytest.mark.slow
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

    def test_seed_repeatability(self):
        out = StringIO()
        cmd_args = ("mass_create_tool", "-p", "3", "-u", "2", "-at", "2", "-dt", "2", "-att", "3", "-dtt", "3", "-ap", "2", "-dp", "2", "-s", "8518751")

        def _get_snapshot(extra_args=()):
            call_command(*cmd_args, *extra_args, stdout=out)
            return {name: sorted(str(obj) for obj in model.objects.all()) for name, model in self.name_to_model.items()}

        seed_snapshot = _get_snapshot()
        seed_snapshot2 = _get_snapshot(("--wipe",))
        self.assertEqual(seed_snapshot, seed_snapshot2)
