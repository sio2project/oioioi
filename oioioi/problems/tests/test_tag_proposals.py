# coding: utf-8

import urllib.parse

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from oioioi.base.tests import TestCase
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagProposal,
    DifficultyTag,
    DifficultyTagProposal,
    Problem,
)
from oioioi.problems.tests.utilities import AssertContainsOnlyMixin


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
            reverse(self.view_name), urllib.parse.urlencode(parameters)
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
        self.assertEqual(AggregatedAlgorithmTagProposal.object.count(), 0)
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
        self.assertEqual(AggregatedAlgorithmTagProposal.object.count(), 2)
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
        self.assertEquals(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=problem, tag=AlgorithmTag.objects.get(name='dp')
            ).amount, 1
        )
        self.assertEquals(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=problem,
                tag=AlgorithmTag.objects.get(name='knapsack'),
            ).amount, 1
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='easy'), user=user
            ).exists()
        )

        problem = Problem.object.get(pk=0)
        user = User.objects.get(username='test_user')

        response = self.client.post(
            self.url,
            {
                'tags[]': ["Longest common increasing subsequence", "Dynamic programming", "Greedy"],
                'difficulty': '  \t    \r\n MEDIUM   \t     \n  ',
                'user': 'test_user',
                'problem': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AlgorithmTagProposal.objects.count(), 5)
        self.assertEqual(AggregatedAlgorithmTagProposal.object.count(), 4)
        self.assertEqual(DifficultyTagProposal.objects.count(), 2)
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem, tag=AlgorithmTag.objects.get(name='lcis'), user=user
            ).exists()
        )
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem, tag=AlgorithmTag.objects.get(name='dp'), user=user
            ).exists()
        )
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem,
                tag=AlgorithmTag.objects.get(name='greedy'),
                user=user,
            ).exists()
        )
        self.assertEquals(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=problem, tag=AlgorithmTag.objects.get(name='greedy')
            ).amount, 1
        )
        self.assertEquals(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=problem, tag=AlgorithmTag.objects.get(name='lcis')
            ).amount, 1
        )
        self.assertEquals(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=problem, tag=AlgorithmTag.objects.get(name='dp')
            ).amount, 2
        )
        self.assertEquals(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=problem,
                tag=AlgorithmTag.objects.get(name='knapsack'),
            ).amount, 1
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='medium'), user=user
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

