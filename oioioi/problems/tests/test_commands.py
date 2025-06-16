from io import StringIO
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError
from django.contrib.auth import get_user_model
from oioioi.problems.models import (
    Problem,
    AlgorithmTag,
    DifficultyTag,
    AlgorithmTagThrough,
    DifficultyTagThrough,
    AlgorithmTagProposal,
    DifficultyTagProposal,
    ProblemSite,
)

User = get_user_model()

@override_settings(DEBUG=True)
class TestMassCreateTool(TestCase):
    name_to_model = {
        'problems': Problem,
        'problems': ProblemSite,
        'users': User,
        'algotags': AlgorithmTag,
        'difftags': DifficultyTag,
        'algothrough': AlgorithmTagThrough,
        'diffthrough': DifficultyTagThrough,
        'algoproposals': AlgorithmTagProposal,
        'diffproposals': DifficultyTagProposal,
    }

    def _assert_model_counts(self, expected_counts):
        for name, model in self.name_to_model.items():
            count = model.objects.count()
            expected_count = expected_counts.get(name, 0)
            assert count == expected_count, f"Expected {expected_count} {name}, got {count}" 

    def test_long_flags(self):
        out = StringIO()
        call_command(
            'mass_create_tool',
            '--problems', '10',
            '--users', '10',
            '--algotags', '5',
            '--difftags', '5',
            '--algothrough', '20',
            '--diffthrough', '8',
            '--algoproposals', '50',
            '--diffproposals', '50',
            stdout=out,
        )
        self._assert_model_counts({
            'problems': 10,
            'users': 10,
            'algotags': 5,
            'difftags': 5,
            'algothrough': 20,
            'diffthrough': 8,
            'algoproposals': 50,
            'diffproposals': 50,
        })

        call_command(
            'mass_create_tool',
            '--problems', '10',
            '--users', '10',
            '--algotags', '5',
            '--difftags', '5',
            '--algothrough', '20',
            '--diffthrough', '8',
            '--algoproposals', '50',
            '--diffproposals', '50',
            '--wipe',
            stdout=out,
        )
        self._assert_model_counts({
            'problems': 10,
            'users': 10,
            'algotags': 5,
            'difftags': 5,
            'algothrough': 20,
            'diffthrough': 8,
            'algoproposals': 50,
            'diffproposals': 50,
        })
        call_command('mass_create_tool', '--wipe')
        self._assert_model_counts({})

    def test_short_flags(self):
        out = StringIO()
        call_command(
            'mass_create_tool',
            '-p', '10',
            '-u', '10',
            '-at', '5',
            '-dt', '5',
            '-att', '20',
            '-dtt', '8',
            '-ap', '50',
            '-dp', '50',
            stdout=out,
        )
        self._assert_model_counts({
            'problems': 10,
            'users': 10,
            'algotags': 5,
            'difftags': 5,
            'algothrough': 20,
            'diffthrough': 8,
            'algoproposals': 50,
            'diffproposals': 50,
        })
        call_command(
            'mass_create_tool',
            '-p', '10',
            '-u', '10',
            '-at', '5',
            '-dt', '5',
            '-att', '20',
            '-dtt', '8',
            '-ap', '50',
            '-dp', '50',
            '-w',
            stdout=out,
        )

        self._assert_model_counts({
            'problems': 10,
            'users': 10,
            'algotags': 5,
            'difftags': 5,
            'algothrough': 20,
            'diffthrough': 8,
            'algoproposals': 50,
            'diffproposals': 50,
        })
        call_command('mass_create_tool', '-w')
        self._assert_model_counts({})

    @override_settings(DEBUG=False)
    def test_debug_false(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '10',
                '-u', '10',
                '-at', '5',
                '-dt', '5',
                '-att', '20',
                '-dtt', '8',
                '-ap', '50',
                '-dp', '50',
                stdout=out,
            )

    def test_invalid_amount(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '10',
                '-u', '10',
                '-at', '5',
                '-dt', '-5',
                '-att', '20',
                '-dtt', '8',
                '-ap', '50',
                '-dp', '50',
                stdout=out,
            )

    def test_invalid_through_amount(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '7',
                '-at', '5',
                '-att', '40',
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '7',
                '-dt', '5',
                '-dtt', '10',
                stdout=out,
            )

    def test_invalid_proposal_amount(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '1',
                '-u', '1',
                '-ap', '1',
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '1',
                '-at', '1',
                '-ap', '1',
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-u', '1',
                '-at', '1',
                '-ap', '1',
                stdout=out,
            )

        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '1',
                '-u', '1',
                '-dp', '1',
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-p', '1',
                '-dt', '1',
                '-dp', '1',
                stdout=out,
            )
        with self.assertRaises(CommandError):
            call_command(
                'mass_create_tool',
                '-u', '1',
                '-dt', '1',
                '-dp', '1',
                stdout=out,
            )

    def test_seed_repeatability(self):
        out = StringIO()
        call_command(
            'mass_create_tool',
            '-p', '10',
            '-u', '10',
            '-at', '5',
            '-dt', '5',
            '-att', '20',
            '-dtt', '8',
            '-ap', '50',
            '-dp', '50',
            '-s', '8518751',
            stdout=out,
        )

        seed_snapshot = {}
        for name, model in self.name_to_model.items():
            seed_snapshot[name] = sorted(str(obj) for obj in model.objects.all())

        call_command(
            'mass_create_tool',
            '-p', '10',
            '-u', '10',
            '-at', '5',
            '-dt', '5',
            '-att', '20',
            '-dtt', '8',
            '-ap', '50',
            '-dp', '50',
            '-s', '8518751',
            '-w',
            stdout=out,
        )

        seed_snapshot2 = {}
        for name, model in self.name_to_model.items():
            seed_snapshot2[name] = sorted(str(obj) for obj in model.objects.all())

        self.assertEqual(seed_snapshot, seed_snapshot2)
