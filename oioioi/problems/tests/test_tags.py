# coding: utf-8

import csv
import os.path
import random

import six.moves.urllib.parse
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from six.moves import range

from oioioi.base.tests import TestCase
from oioioi.problems.management.commands import (
    create_new_algorithm_tags,
    create_problem_names,
    migrate_old_origin_tags_copy_problem_statements,
    migrate_old_origin_tags_create_new_tags,
)
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagLocalization,
    AlgorithmTagProposal,
    DifficultyTag,
    DifficultyTagProposal,
    OriginInfoCategory,
    OriginInfoCategoryLocalization,
    OriginInfoValue,
    OriginInfoValueLocalization,
    OriginTag,
    OriginTagLocalization,
    Problem,
    ProblemName,
    ProblemStatement,
    Tag,
    TagThrough,
)
from oioioi.problems.tests.utilities import AssertContainsOnlyMixin


class TestCreateProblemNames(TestCase):
    basedir = os.path.dirname(__file__)
    filename = os.path.join(basedir, 'test_files', 'legacy_origin_tags.txt')
    names_translations = {}

    def setUp(self):
        random.seed(42)

        with open(self.filename, mode='r') as tags_file:
            self.legacy_origin_tags = set(tags_file.read().split(','))

        tag_eng = Tag.objects.create(name='eng')

        for tag_name in self.legacy_origin_tags:
            legacy_origin_tag = Tag.objects.create(name=tag_name)
            for i in range(random.randrange(10)):
                short_name = 'zad%d' % i
                legacy_name_en = tag_name + ' problem %d' % i
                legacy_name_pl = tag_name + ' zadanie %d' % i

                self.names_translations[legacy_name_en] = legacy_name_pl
                self.names_translations[legacy_name_pl] = legacy_name_en

                problem_en = Problem.objects.create(
                    legacy_name=legacy_name_en, short_name=short_name
                )
                problem_pl = Problem.objects.create(
                    legacy_name=legacy_name_pl, short_name=short_name
                )

                TagThrough.objects.create(problem=problem_en, tag=tag_eng)
                TagThrough.objects.create(problem=problem_en, tag=legacy_origin_tag)
                TagThrough.objects.create(problem=problem_pl, tag=legacy_origin_tag)

    def test_create_problem_names_command(self):
        problems_count = Problem.objects.all().count()

        self.assertTrue(problems_count > 1)
        self.assertEqual(Tag.objects.all().count(), len(self.legacy_origin_tags) + 1)

        manager = create_problem_names.Command()
        manager.run_from_argv(
            [
                'manage.py',
                'create_problem_names',
                '-f',
                self.filename,
            ]
        )

        self.assertEqual(ProblemName.objects.all().count(), 2 * problems_count)

        tag_eng = Tag.objects.get(name='eng')
        for problem in Problem.objects.all():
            problem_names = problem.names.all()
            self.assertEqual(problem_names.count(), 2)

            if problem in tag_eng.problems.all():
                legacy_name_en = problem.legacy_name
                legacy_name_pl = self.names_translations[legacy_name_en]
            else:
                legacy_name_pl = problem.legacy_name
                legacy_name_en = self.names_translations[legacy_name_pl]

            self.assertTrue(
                problem_names.filter(name=legacy_name_en, language='en').exists()
            )
            self.assertTrue(
                problem_names.filter(name=legacy_name_pl, language='pl').exists()
            )


class TestCreateNewAlgorithmTags(TestCase):
    basedir = os.path.dirname(__file__)
    filename = os.path.join(basedir, 'test_files', 'new_algorithm_tags.csv')

    def setUp(self):
        AlgorithmTag.objects.create(name='unique_tag')

    def tearDown(self):
        AlgorithmTag.objects.all().delete()

    def _test_create_new_algorithm_tags_command(
        self, argv, filename, delete=False, dry_run=False
    ):
        algorithm_tags_count_before = AlgorithmTag.objects.count()
        self.assertTrue(algorithm_tags_count_before, 1)

        manager = create_new_algorithm_tags.Command()
        manager.run_from_argv(argv)

        algorithm_tags_count_after = AlgorithmTag.objects.count()

        with open(filename, mode='r') as csv_file:
            created_algorithm_tags_expected_count = len(csv_file.readlines()) - 1

        if delete:
            if dry_run:
                self.assertEqual(
                    algorithm_tags_count_after, algorithm_tags_count_before
                )
                self.assertTrue(AlgorithmTag.objects.filter(name='unique_tag').exists())
            else:
                self.assertEqual(
                    algorithm_tags_count_after, created_algorithm_tags_expected_count
                )
                self.assertFalse(
                    AlgorithmTag.objects.filter(name='unique_tag').exists()
                )
        else:
            if dry_run:
                self.assertEqual(
                    algorithm_tags_count_after, algorithm_tags_count_before
                )
            else:
                self.assertEqual(
                    algorithm_tags_count_after,
                    algorithm_tags_count_before + created_algorithm_tags_expected_count,
                )
            self.assertTrue(AlgorithmTag.objects.filter(name='unique_tag').exists())

        if not dry_run:
            with open(filename, mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file, delimiter=',')
                for row in csv_reader:
                    new_tag = AlgorithmTag.objects.get(name=row['name'])
                    new_tag_localizations = AlgorithmTagLocalization.objects.filter(
                        algorithm_tag=new_tag
                    )

                    self.assertEqual(new_tag_localizations.count(), 2)
                    for tag_name in ['full_name_pl', 'full_name_en']:
                        self.assertTrue(
                            new_tag_localizations.filter(
                                full_name=row[tag_name]
                            ).exists()
                        )

    def test_create_new_algorithm_tags_command_with_delete_no_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '--file',
                self.filename,
                '-d',
            ],
            self.filename,
            delete=True,
        )

    def test_create_new_algorithm_tags_command_no_delete_no_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '-f',
                self.filename,
            ],
            self.filename,
        )

    def test_create_new_algorithm_tags_command_no_delete_with_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '-f',
                self.filename,
                '--dry_run',
            ],
            self.filename,
            dry_run=True,
        )

    def test_create_new_algorithm_tags_command_with_delete_with_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '-f',
                self.filename,
                '--delete',
                '-dr',
            ],
            self.filename,
            delete=True,
            dry_run=True,
        )


class TestMigrateOldOriginTagsCreateNewTags(TestCase):
    problems_names = [
        'Kurczak',
        'Herbata',
        'Mleko',
        'Banan',
        'Kanapka',
        'Tost',
        'Ketchup',
        'Pizza',
        'Frytki',
        'Kebab',
        'Piwo',
        'Wino',
        'Czekolada',
        'Kakao',
        'Marchewka',
        'Por',
    ]
    tags_names = [
        'ONTAK2013',
        'ONTAK2012',
        'AMPPZ2012',
        'AMPPZ2011',
        'BOI2015',
        'BOI2008',
        'ILOCAMP11',
        'SERWY2010',
    ]

    def setUp(self):
        for name in self.problems_names:
            Problem.objects.create(
                legacy_name=name,
                short_name=name.lower()[:3],
                visibility='PU',
            )

        Tag.objects.create(name='eng')
        for name in self.tags_names:
            Tag.objects.create(name=name)

        for i, name in enumerate(self.problems_names):
            tag = Tag.objects.get(name=self.tags_names[i % len(self.tags_names)])
            problem = Problem.objects.get(legacy_name=name)
            TagThrough.objects.create(problem=problem, tag=tag)

    def test_migrate_old_origin_tags_create_new_tags_command(self):
        basedir = os.path.dirname(__file__)
        filename = os.path.join(
            basedir, 'test_files', 'old_origin_tags_to_create_tags.csv'
        )
        manager = migrate_old_origin_tags_create_new_tags.Command()
        manager.run_from_argv(
            [
                'manage.py',
                'migrate_old_origin_tags_create_new_tags',
                '-f',
                filename,
            ]
        )

        origin_tag_count = OriginTag.objects.count()
        self.assertEqual(origin_tag_count, 5)
        self.assertEqual(OriginInfoCategory.objects.count(), origin_tag_count)
        self.assertEqual(OriginInfoValue.objects.count(), Tag.objects.count() - 1)

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                old_tags = Tag.objects.filter(name__istartswith=row['OriginTag_name'])
                if row['OriginTag_name'] == 'proserwy':
                    old_tags = Tag.objects.filter(name__istartswith='serwy')
                old_tags_problems = Problem.objects.none()
                for old_tag in old_tags:
                    old_tags_problems |= old_tag.problems.all()
                old_tags_problems_set = set(old_tags_problems)

                origin_tag = OriginTag.objects.get(name=row['OriginTag_name'])
                origin_tag_problems_set = set(origin_tag.problems.all())
                origin_tag_localizations = OriginTagLocalization.objects.filter(
                    origin_tag=origin_tag
                )

                origin_info_category = OriginInfoCategory.objects.get(
                    parent_tag=origin_tag
                )
                origin_info_category_localizations = (
                    OriginInfoCategoryLocalization.objects.filter(
                        origin_info_category=origin_info_category
                    )
                )

                origin_info_value = OriginInfoValue.objects.get(
                    parent_tag=origin_tag,
                    value=row['OriginInfoValue_value'],
                )
                origin_info_value_localizations = (
                    OriginInfoValueLocalization.objects.filter(
                        origin_info_value=origin_info_value
                    )
                )

                self.assertTrue(old_tags_problems_set == origin_tag_problems_set)
                self.assertTrue(len(old_tags_problems_set) in (2, 4))
                self.assertEqual(origin_tag_localizations.count(), 2)
                for tag_name in ['full_name_EN', 'full_name_PL']:
                    colname = 'OriginTagLocalization_' + tag_name
                    self.assertTrue(
                        origin_tag_localizations.filter(full_name=row[colname]).exists()
                    )

                self.assertEqual(origin_info_category.name, 'year')
                self.assertEqual(origin_info_category.order, 1)
                self.assertEqual(origin_info_category_localizations.count(), 2)
                for tag_name in ['full_name_EN', 'full_name_PL']:
                    colname = 'OriginInfoCategoryLocalization_' + tag_name
                    self.assertTrue(
                        origin_info_category_localizations.filter(
                            full_name=row[colname]
                        ).exists()
                    )

                self.assertEqual(int(origin_info_value.value), -origin_info_value.order)
                self.assertEqual(origin_info_value_localizations.count(), 2)
                for tag_name in ['full_value_EN', 'full_value_PL']:
                    colname = 'OriginInfoValueLocalization_' + tag_name
                    self.assertTrue(
                        origin_info_value_localizations.filter(
                            full_value=row[colname]
                        ).exists()
                    )


class TestMigrateOldOriginTagsCopyProblemStatements(TestCase):
    description = {
        'OIG1': {'name_en': 'Kurczak en', 'name_pl': 'Kurczak pl'},
        'IOI2009': {'name_en': 'Herbata en', 'name_pl': 'Herbata pl'},
        'IOI2008': {'name_en': 'Mleko en', 'name_pl': 'Mleko pl'},
        'CEOI2011': {'name_en': 'Banan en', 'name_pl': 'Banan pl'},
        'CEOI2010': {
            'name_en': 'Kanapka en',
            'name_pl': 'Kanapka pl',
        },
        'CEOI2004': {
            'name_en': 'Tost en',
            'name_pl': 'Tost pl',
        },
        'PA2013': {
            'name_en': 'Ketchup en',
            'name_pl': 'Ketchup pl',
        },
        'PA2012': {
            'name_en': 'Pizza en',
            'name_pl': 'Pizza pl',
        },
        'OI21': {
            'name_en': 'Frytki en',
            'name_pl': 'Frytki pl',
        },
        'OI20': {
            'name_en': 'Kebab en',
            'name_pl': 'Kebab pl',
        },
        'OI19': {
            'name_en': 'Piwo en',
            'name_pl': 'Piwo pl',
        },
        'ONTAK2013': {
            'name_en': 'Wino en',
            'name_pl': 'Wino pl',
        },
        'ONTAK2012': {
            'name_en': 'Czekolada en',
            'name_pl': 'Czekolada pl',
        },
        'AMPPZ2012': {
            'name_en': 'Kakao en',
            'name_pl': 'Kakao pl',
        },
        'AMPPZ2011': {
            'name_en': 'Marchewka en',
            'name_pl': 'Marchewka pl',
        },
        'ILOCAMP11': {
            'name_en': 'Por en',
            'name_pl': 'Por pl',
        },
    }

    def setUp(self):
        random.seed(42)
        tag_eng = Tag.objects.create(name='eng')

        for tag_name in self.description:
            tag = Tag.objects.create(name=tag_name)
            problems = self.description[tag_name]

            problem_en = Problem.objects.create(
                legacy_name=problems['name_en'],
                short_name=problems['name_en'].lower()[:3],
                visibility='PU',
            )
            problem_pl = Problem.objects.create(
                legacy_name=problems['name_pl'],
                short_name=problems['name_pl'].lower()[:3],
                visibility='PU',
            )

            if random.choice([True, False]):
                ProblemStatement.objects.create(
                    problem=problem_en,
                    content='data:problems/1/en.pdf:raw:en-pdf',
                )
                ProblemStatement.objects.create(
                    problem=problem_en,
                    content='data:problems/1/en.html:raw:en-html',
                )
                ProblemStatement.objects.create(
                    problem=problem_pl,
                    content='data:problems/1/pl.html:raw:pl-html',
                )
            else:
                ProblemStatement.objects.create(
                    problem=problem_en,
                    language='en',
                    content='data:problems/1/en.html:raw:en-html',
                )
                ProblemStatement.objects.create(
                    problem=problem_pl,
                    language='pl',
                    content='data:problems/1/pl.pdf:raw:pl-pdf',
                )

            TagThrough.objects.create(problem=problem_en, tag=tag_eng)
            TagThrough.objects.create(problem=problem_en, tag=tag)
            TagThrough.objects.create(problem=problem_pl, tag=tag)

    def test_migrate_old_origin_tags_create_copy_problem_statements_command(self):
        problems_count_before = Problem.objects.count()

        basedir = os.path.dirname(__file__)
        filename = os.path.join(
            basedir, 'test_files', 'old_origin_tags_to_copy_statements.csv'
        )
        manager = migrate_old_origin_tags_copy_problem_statements.Command()
        manager.run_from_argv(
            [
                'manage.py',
                'migrate_old_origin_tags_copy_problem_statements',
                '-f',
                filename,
                '-m',
            ]
        )

        self.assertEqual(Problem.objects.count(), problems_count_before)

        tag_copied = Tag.objects.get(name='copied')

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                problems = self.description[row['Tag_name']]
                problem_en = Problem.objects.get(legacy_name=problems['name_en'])
                problem_pl = Problem.objects.get(legacy_name=problems['name_pl'])

                if row['language_version_with_no_origin'] == 'en':
                    self.assertTrue(problem_en in tag_copied.problems.all())

                    problem_en_statement = [
                        problem
                        for problem in ProblemStatement.objects.filter(
                            problem=problem_en
                        )
                        if str(problem.content).endswith('.html')
                    ][0]
                    problem_pl_copied_statement = ProblemStatement.objects.filter(
                        problem=problem_pl, content=problem_en_statement.content
                    ).get()
                    problem_pl_original_statement = (
                        ProblemStatement.objects.filter(problem=problem_pl)
                        .exclude(content=problem_pl_copied_statement.content)
                        .get()
                    )

                    self.assertEqual(problem_pl_copied_statement.language, 'en')
                    self.assertEqual(problem_pl_original_statement.language, 'pl')
                else:
                    self.assertTrue(problem_pl in tag_copied.problems.all())

                    problem_pl_statement = ProblemStatement.objects.filter(
                        problem=problem_pl
                    ).get()
                    problem_en_copied_statement = ProblemStatement.objects.filter(
                        problem=problem_en, content=problem_pl_statement.content
                    ).get()
                    problem_en_original_statements = ProblemStatement.objects.filter(
                        problem=problem_en
                    ).exclude(content=problem_en_copied_statement.content)
                    problem_en_original_statement = [
                        problem
                        for problem in problem_en_original_statements
                        if str(problem.content).endswith('.html')
                    ][0]

                    self.assertEqual(problem_en_copied_statement.language, 'pl')
                    self.assertEqual(problem_en_original_statement.language, 'en')


class TestAlgorithmTagsProposalHintsBase(TestCase):
    """Abstract base class with getting url utility for algorithm tags proposal tests."""

    fixtures = [
        'test_users',
        'test_contest',
        'test_problem_packages',
        'test_problem_site',
        'test_algorithm_tags',
    ]
    view_name = 'get_algorithm_tag_proposal_hints'

    def get_query_url(self, parameters):
        return '{}?{}'.format(
            reverse(self.view_name), six.moves.urllib.parse.urlencode(parameters)
        )


@override_settings(LANGUAGE_CODE='en')
class TestAlgorithmTagsProposalHintsEnglish(TestAlgorithmTagsProposalHintsBase):
    def test_tag_proposal_hints_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        response = self.client.get(self.get_query_url({'query': 'pLeCaK'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Knapsack problem')
        self.assertNotContains(response, 'Problem plecakowy')
        self.assertNotContains(response, 'pLeCaK')
        self.assertNotContains(response, 'plecak')
        self.assertNotContains(response, 'Longest common increasing subsequence')

        response = self.client.get(self.get_query_url({'query': 'PROBLEM'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Knapsack problem')
        self.assertNotContains(response, 'Problem plecakowy')
        self.assertNotContains(response, 'Longest common increasing subsequence')

        response = self.client.get(self.get_query_url({'query': 'dynam'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dynamic programming')
        self.assertNotContains(response, 'dp')
        self.assertNotContains(response, 'Programowanie dynamiczne')

        response = self.client.get(self.get_query_url({'query': 'greedy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Greedy')
        self.assertNotContains(response, 'Dynamic programming')
        self.assertNotContains(response, 'XYZ')

        # Use a byte string in the query to ensure a proper url encoding.
        response = self.client.get(self.get_query_url({'query': 'najdłuższy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'lcis')

        response = self.client.get(self.get_query_url({'query': 'l'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'lcis')
        self.assertNotContains(response, 'Problem plecakowy')


@override_settings(LANGUAGE_CODE='pl')
class TestAlgorithmTagsProposalHintsPolish(TestAlgorithmTagsProposalHintsBase):
    def test_tag_proposal_hints_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        response = self.client.get(self.get_query_url({'query': 'plecak'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Problem plecakowy')
        self.assertNotContains(response, 'Knapsack problem')
        self.assertNotContains(response, 'Longest common increasing subsequence')

        response = self.client.get(self.get_query_url({'query': 'dynam'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Programowanie dynamiczne')
        self.assertNotContains(response, 'dp')
        self.assertNotContains(response, 'Dynamic programming')

        response = self.client.get(self.get_query_url({'query': 'greedy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, b'Zach\u0142anny')
        self.assertNotContains(response, 'Greedy')

        # Use a byte string in the query to ensure a proper url encoding.
        response = self.client.get(self.get_query_url({'query': 'ZAchłan'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, b'Zach\u0142anny')
        self.assertNotContains(response, 'Greedy')

        response = self.client.get(self.get_query_url({'query': 'longest'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(response, 'lcis')

        response = self.client.get(self.get_query_url({'query': 'lcis'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(response, 'lcis')


class TestAlgorithmTagLabel(TestCase):
    fixtures = ['test_algorithm_tags']
    view_name = 'get_algorithm_tag_label'

    def get_tag_labels(self, parameters):
        url = '{}?{}'.format(
            reverse(self.view_name), six.moves.urllib.parse.urlencode(parameters)
        )
        return self.client.get(url)

    def test_algorithm_tag_label_view(self):
        response = self.get_tag_labels(
            {'name': 'Najdłuższy wspólny podciąg rosnący', 'proposed': '-1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )

        response = self.get_tag_labels(
            {'name': 'Programowanie dynamiczne', 'proposed': '-1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Programowanie dynamiczne')

        response = self.get_tag_labels({'name': 'Knapsack problem', 'proposed': '-1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Knapsack problem')

        invalid_query_data = [
            {'name': 'Programowanie dynamiczne', 'proposed': '0'},
            {'name': '', 'proposed': '-1'},
            {'name': 'XYZ', 'proposed': '-1'},
        ]
        for query_data in invalid_query_data:
            response = self.get_tag_labels(query_data)
            self.assertEqual(response.status_code, 404)


class TestSaveProposals(TestCase):
    fixtures = [
        'test_users',
        'test_problem_search',
        'test_algorithm_tags',
        'test_difficulty_tags',
    ]
    url = reverse('save_proposals')

    def test_save_proposals_view(self):
        problem = Problem.objects.get(pk=0)
        user = User.objects.get(username='test_admin')

        self.assertEqual(AlgorithmTagProposal.objects.count(), 0)
        self.assertEqual(DifficultyTagProposal.objects.count(), 0)

        response = self.client.post(
            self.url,
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'difficulty': '  \r    \t\n        Easy   \n     \t  ',
                'user': 'test_admin',
                'problem': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AlgorithmTagProposal.objects.count(), 2)
        self.assertEqual(DifficultyTagProposal.objects.count(), 1)
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem, tag=AlgorithmTag.objects.get(name='dp'), user=user
            ).exists()
        )
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem,
                tag=AlgorithmTag.objects.get(name='knapsack'),
                user=user,
            ).exists()
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='easy'), user=user
            ).exists()
        )

        invalid_query_data = [
            {},
            {
                'difficulty': 'Easy',
                'user': 'test_admin',
                'problem': '0',
            },
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'user': 'test_admin',
                'problem': '0',
            },
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'difficulty': 'Easy',
                'problem': '0',
            },
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'difficulty': 'Easy',
                'user': 'test_admin',
            },
        ]

        for q_data in invalid_query_data:
            response = self.client.post(self.url, q_data)
            self.assertEqual(response.status_code, 400)


class TestProblemSearchOrigin(TestCase, AssertContainsOnlyMixin):
    fixtures = ['test_problem_search_origin']
    url = reverse('problemset_main')
    task_names = all_values = [
        '0_private',
        '0_public',
        '1_pa',
        '2_pa_2011',
        '3_pa_2011_r1',
        '3_pa_2011_r2',
        '2_pa_2012',
        '3_pa_2012_r1',
    ]

    def test_search_origintag(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': 'pa'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, self.task_names[2:])

        response = self.client.get(self.url, {'origin': ['pa', 'oi']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

    def test_search_origininfovalue(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': ['pa_r1']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1', '3_pa_2012_r1'])

        response = self.client.get(self.url, {'origin': ['pa', 'pa_r1']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1', '3_pa_2012_r1'])

    def test_search_origininfovalue_invalid(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': ['r1']})
        self.assertEqual(response.status_code, 404)

        response = self.client.get(self.url, {'origin': ['pa_2077']})
        self.assertEqual(response.status_code, 404)

        response = self.client.get(self.url, {'origin': ['pa_2011_r1']})
        self.assertEqual(response.status_code, 404)

    def test_search_origininfovalue_multiple(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': ['pa_2011', 'pa_r1']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1'])

        response = self.client.get(self.url, {'origin': ['pa_2011', 'pa_r1', 'pa_r2']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1', '3_pa_2011_r2'])

        response = self.client.get(self.url, {'origin': ['pa_r1', 'pa_r2']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(
            response, ['3_pa_2011_r1', '3_pa_2011_r2', '3_pa_2012_r1']
        )

        response = self.client.get(
            self.url, {'origin': ['pa_2011', 'pa_2012', 'pa_r1', 'pa_r2']}
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(
            response, ['3_pa_2011_r1', '3_pa_2011_r2', '3_pa_2012_r1']
        )

        response = self.client.get(self.url, {'origin': ['pa_2012', 'pa_r2']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])


class TestProblemSearchHintsTags(TestCase, AssertContainsOnlyMixin):
    fixtures = [
        'test_origin_tags',
        'test_algorithm_tags',
        'test_difficulty_tags',
    ]
    url = reverse('get_search_hints', args=('public',))
    category_url = reverse('get_origininfocategory_hints')
    selected_origintag_url = reverse('get_selected_origintag_hints')
    hints = all_values = [
        'very-easy',
        'easy',
        'medium',
        'hard',
        'very-hard',
        'dp',
        'lcis',
        'pa_2011',
        'pa_2012',
        'pa_r1',
        'pa_r2',
        'oi_2011',
        'oi_r1',
        'oi_r2',
        'origintag',
        'round',
        'year',
    ]

    def get_query_url(self, parameters):
        return self.url + '?' + six.moves.urllib.parse.urlencode(parameters)

    @override_settings(LANGUAGE_CODE="en")
    def test_search_hints_tags_basic(self):
        self.client.get('/c/c/')

        response = self.client.get(self.get_query_url({'q': 'najdłuższy'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['lcis'])

        response = self.client.get(self.get_query_url({'q': 'easy'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['very-easy', 'easy'])

        response = self.client.get(self.get_query_url({'q': 'Mediu'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['medium'])

        response = self.client.get(self.get_query_url({'q': 'PROGRA'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['dp'])

        response = self.client.get(self.get_query_url({'q': 'dYNAM'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['dp'])

        response = self.client.get(self.get_query_url({'q': 'dp'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'increasing'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['lcis'])

    def test_search_hints_origininfo(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'pa_'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_2011', 'pa_r1', 'pa_r2'])

        response = self.client.get(self.url, {'q': '2011'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_2011', 'oi_2011'])

        response = self.client.get(self.url, {'q': 'Round'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_r1', 'pa_r2', 'oi_r1', 'oi_r2'])

        response = self.client.get(self.url, {'q': 'Potyczki Algorytmiczne'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['origintag', 'round', 'year'])

    @override_settings(LANGUAGE_CODE="en")
    def test_category_hints(self):
        self.client.get('/c/c/')
        response = self.client.get(
            self.category_url, {'category': 'round', 'q': 'Potyczki Algorytmiczne'}
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_r1', 'pa_r2'])

    @override_settings(LANGUAGE_CODE="en")
    def test_selected_origintag_hints_en(self):
        self.client.get('/c/c/')
        response = self.client.get(
            self.selected_origintag_url, {'q': 'Potyczki Algorytmiczne'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pa')
        self.assertContains(response, 'Potyczki Algorytmiczne')
        self.assertContains(response, 'Potyczki Algorytmiczne - Year')
        self.assertContains(response, 'Potyczki Algorytmiczne - Round')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Rok')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Runda')
        self.assertNotContains(response, 'pa_r1')
        self.assertNotContains(response, 'pa_r2')
        self.assertNotContains(response, 'pa_2011')
        self.assertNotContains(response, 'pa_2012')

    @override_settings(LANGUAGE_CODE="pl")
    def test_selected_origintag_hints_pl(self):
        self.client.get('/c/c/')
        response = self.client.get(
            self.selected_origintag_url, {'q': 'Potyczki Algorytmiczne'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pa')
        self.assertContains(response, 'Potyczki Algorytmiczne')
        self.assertContains(response, 'Potyczki Algorytmiczne - Rok')
        self.assertContains(response, 'Potyczki Algorytmiczne - Runda')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Year')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Round')
        self.assertNotContains(response, 'pa_r1')
        self.assertNotContains(response, 'pa_r2')
        self.assertNotContains(response, 'pa_2011')
        self.assertNotContains(response, 'pa_2012')
