# coding: utf-8

from django.test import TestCase
from django.apps import apps
from django.contrib.auth.models import User
from oioioi.problems.models import (
    AggregatedDifficultyTagProposal,
    AggregatedAlgorithmTagProposal,
    AlgorithmTagProposal,
    DifficultyTagProposal,
    Problem,
    AlgorithmTag,
    DifficultyTag,
)
import importlib

# Dynamically import the function applying data migration for AggregatedTagProposals.
# This is necessary, since the name of the migration file causes a syntax error when imported normally.
migration_module = importlib.import_module('oioioi.problems.migrations.0033_populate_aggregated_tag_proposals')
populate_aggregated_tag_proposals = getattr(migration_module, 'populate_aggregated_tag_proposals')

class PopulateAggregatedTagProposalsTest(TestCase):
    fixtures = [
        'test_users',
        'test_problem_search',
        'test_algorithm_tags',
        'test_difficulty_tags',
    ]

    def setUp(self):
        self.problem1 = Problem.objects.get(pk=1)
        self.problem2 = Problem.objects.get(pk=2)
        self.algorithm_tag1 = AlgorithmTag.objects.get(pk=1)
        self.algorithm_tag2 = AlgorithmTag.objects.get(pk=2)
        self.difficulty_tag1 = DifficultyTag.objects.get(pk=1)
        self.difficulty_tag2 = DifficultyTag.objects.get(pk=2)
        self.user1 = User.objects.get(pk=1000)
        self.user2 = User.objects.get(pk=1001)
        self.user3 = User.objects.get(pk=1002)

        DifficultyTagProposal.objects.bulk_create([
            DifficultyTagProposal(problem=self.problem1, tag=self.difficulty_tag1, user=self.user1),
            DifficultyTagProposal(problem=self.problem1, tag=self.difficulty_tag1, user=self.user2),
            DifficultyTagProposal(problem=self.problem1, tag=self.difficulty_tag2, user=self.user3),
            DifficultyTagProposal(problem=self.problem2, tag=self.difficulty_tag2, user=self.user2),
        ])

        AlgorithmTagProposal.objects.bulk_create([
            AlgorithmTagProposal(problem=self.problem1, tag=self.algorithm_tag1, user=self.user1),
            AlgorithmTagProposal(problem=self.problem1, tag=self.algorithm_tag2, user=self.user1),
            AlgorithmTagProposal(problem=self.problem1, tag=self.algorithm_tag1, user=self.user3),
            AlgorithmTagProposal(problem=self.problem2, tag=self.algorithm_tag2, user=self.user1),
            AlgorithmTagProposal(problem=self.problem2, tag=self.algorithm_tag1, user=self.user2),
            AlgorithmTagProposal(problem=self.problem2, tag=self.algorithm_tag2, user=self.user2),
            AlgorithmTagProposal(problem=self.problem2, tag=self.algorithm_tag2, user=self.user3),
        ])

    def test_populate_aggregated_tag_proposals(self):
        AggregatedDifficultyTagProposal.objects.filter(problem=self.problem1).delete()
        AggregatedAlgorithmTagProposal.objects.filter(problem=self.problem2).delete()

        populate_aggregated_tag_proposals(apps, None)

        self.assertEqual(AlgorithmTagProposal.objects.count(), 7)
        self.assertEqual(DifficultyTagProposal.objects.count(), 4)

        self.assertEqual(AggregatedAlgorithmTagProposal.objects.count(), 4)
        self.assertEqual(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=self.problem1, tag=self.algorithm_tag1
            ).amount, 2
        )
        self.assertEqual(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=self.problem1, tag=self.algorithm_tag2
            ).amount, 1
        )
        self.assertEqual(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=self.problem2, tag=self.algorithm_tag1
            ).amount, 1
        )
        self.assertEqual(
            AggregatedAlgorithmTagProposal.objects.get(
                problem=self.problem2, tag=self.algorithm_tag2
            ).amount, 3
        )

        self.assertEqual(AggregatedDifficultyTagProposal.objects.count(), 3)
        self.assertEqual(
            AggregatedDifficultyTagProposal.objects.get(
                problem=self.problem1, tag=self.difficulty_tag1
            ).amount, 2
        )
        self.assertEqual(
            AggregatedDifficultyTagProposal.objects.get(
                problem=self.problem1, tag=self.difficulty_tag2
            ).amount, 1
        )
        self.assertEqual(     
            AggregatedDifficultyTagProposal.objects.get(
                problem=self.problem2, tag=self.difficulty_tag2
            ).amount, 1
        )
        