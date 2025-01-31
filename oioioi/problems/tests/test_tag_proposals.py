# coding: utf-8

import urllib.parse

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from oioioi.base.tests import TestCase
from oioioi.problems.models import (
    AggregatedAlgorithmTagProposal,
    AggregatedDifficultyTagProposal,
    AlgorithmTag,
    AlgorithmTagProposal,
    DifficultyTag,
    DifficultyTagProposal,
    Problem,
)


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



def _get_tag_name_amounts(aggregated_model, problem):
    """Returns a dictionary mapping tag names to their amounts for a given problem."""
    return {
        proposal.tag.name: proposal.amount
        for proposal in aggregated_model.objects.filter(problem=problem)
    }

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
        self.assertEqual(AggregatedAlgorithmTagProposal.objects.count(), 0)
        self.assertEqual(DifficultyTagProposal.objects.count(), 0)
        self.assertEqual(AggregatedDifficultyTagProposal.objects.count(), 0)

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
        self.assertEqual(AggregatedAlgorithmTagProposal.objects.count(), 2)
        self.assertEqual(DifficultyTagProposal.objects.count(), 1)
        self.assertEqual(AggregatedDifficultyTagProposal.objects.count(), 1)
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
        self.assertEqual(
            _get_tag_name_amounts(AggregatedAlgorithmTagProposal, problem),
            {'dp': 1, 'knapsack': 1},
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='easy'), user=user
            ).exists()
        )
        self.assertEqual(
            _get_tag_name_amounts(AggregatedDifficultyTagProposal, problem),
            {'easy': 1},
        )

        problem = Problem.objects.get(pk=0)
        user = User.objects.get(username='test_user')

        response = self.client.post(
            self.url,
            {
                'tags[]': ["Longest common increasing subsequence", "Dynamic programming", "Greedy"],
                'difficulty': '  \t    \r\n Medium   \t     \n  ',
                'user': 'test_user',
                'problem': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AlgorithmTagProposal.objects.count(), 5)
        self.assertEqual(AggregatedAlgorithmTagProposal.objects.count(), 4)
        self.assertEqual(DifficultyTagProposal.objects.count(), 2)
        self.assertEqual(AggregatedDifficultyTagProposal.objects.count(), 2)
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
        self.assertEqual(
            _get_tag_name_amounts(AggregatedAlgorithmTagProposal, problem),
            {'dp': 2, 'knapsack': 1, 'greedy': 1, 'lcis': 1},
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='medium'), user=user
            ).exists()
        )
        self.assertEqual(
            _get_tag_name_amounts(AggregatedDifficultyTagProposal, problem),
            {'easy': 1, 'medium': 1},
        )

        problem = Problem.objects.get(pk=0)
        user = User.objects.get(username='test_user2')

        response = self.client.post(
            self.url,
            {
                'tags[]': ["Greedy"],
                'difficulty': ' Medium  \n  ',
                'user': 'test_user2',
                'problem': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AlgorithmTagProposal.objects.count(), 6)
        self.assertEqual(AggregatedAlgorithmTagProposal.objects.count(), 4)
        self.assertEqual(DifficultyTagProposal.objects.count(), 3)
        self.assertEqual(AggregatedDifficultyTagProposal.objects.count(), 2)
        self.assertEqual(
            _get_tag_name_amounts(AggregatedAlgorithmTagProposal, problem),
            {'dp': 2, 'knapsack': 1, 'greedy': 2, 'lcis': 1},
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='medium'), user=user
            ).exists()
        )
        self.assertEqual(
            _get_tag_name_amounts(AggregatedDifficultyTagProposal, problem),
            {'easy': 1, 'medium': 2},
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

