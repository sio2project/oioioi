from io import StringIO

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

    def test_long_flags(self):
        out = StringIO()
        call_command(
            "mass_create_tool",
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
            stdout=out,
        )
        self._assert_model_counts(
            {
                "problems": 10,
                "users": 10,
                "algotags": 5,
                "difftags": 5,
                "algothrough": 20,
                "diffthrough": 8,
                "algoproposals": 50,
                "diffproposals": 50,
            }
        )

        call_command(
            "mass_create_tool",
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
            "--wipe",
            stdout=out,
        )
        self._assert_model_counts(
            {
                "problems": 10,
                "users": 10,
                "algotags": 5,
                "difftags": 5,
                "algothrough": 20,
                "diffthrough": 8,
                "algoproposals": 50,
                "diffproposals": 50,
            }
        )
        call_command("mass_create_tool", "--wipe")
        self._assert_model_counts({})

    def test_long_flags_contest(self):
        out = StringIO()
        call_command(
            "mass_create_tool",
            "--contestname",
            "demo",
            "--createcontest",
            "--problempackages",
            "test_full_package.tgz",
            "--users",
            "10",
            "--submission_files",
            "sum-correct.cpp",
            "sum-various-results.cpp",
            "--submissions_per_user",
            "3",
            "--wipe",
            stdout=out,
        )
        self._assert_model_counts({"users": 10, "problems": 1, "contests": 1, "submissions": 30}, check_problem_names=False)

    def test_short_flags_contest(self):
        out = StringIO()
        call_command(
            "mass_create_tool",
            "-cn",
            "demo",
            "-cc",
            "-pp",
            "test_full_package.tgz",
            "-u",
            "10",
            "-sf",
            "sum-correct.cpp",
            "sum-various-results.cpp",
            "-spu",
            "3",
            "-w",
            stdout=out,
        )
        self._assert_model_counts({"users": 10, "problems": 1, "contests": 1, "submissions": 30}, check_problem_names=False)

    def test_short_flags(self):
        out = StringIO()
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
        self._assert_model_counts(
            {
                "problems": 10,
                "users": 10,
                "algotags": 5,
                "difftags": 5,
                "algothrough": 20,
                "diffthrough": 8,
                "algoproposals": 50,
                "diffproposals": 50,
            }
        )
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
            "-w",
            stdout=out,
        )

        self._assert_model_counts(
            {
                "problems": 10,
                "users": 10,
                "algotags": 5,
                "difftags": 5,
                "algothrough": 20,
                "diffthrough": 8,
                "algoproposals": 50,
                "diffproposals": 50,
            }
        )
        call_command("mass_create_tool", "-w")
        self._assert_model_counts({})

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
            "-s",
            "8518751",
            stdout=out,
        )

        seed_snapshot = {}
        for name, model in self.name_to_model.items():
            seed_snapshot[name] = sorted(str(obj) for obj in model.objects.all())

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
            "-s",
            "8518751",
            "-w",
            stdout=out,
        )

        seed_snapshot2 = {}
        for name, model in self.name_to_model.items():
            seed_snapshot2[name] = sorted(str(obj) for obj in model.objects.all())

        self.assertEqual(seed_snapshot, seed_snapshot2)
