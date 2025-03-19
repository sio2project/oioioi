# coding: utf-8

import urllib.parse

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from oioioi.base.tests import TestCase
from oioioi.problems.models import (
    AlgorithmTag,
    DifficultyTag,
    Problem,
)
from oioioi.problems.tests.utilities import AssertContainsOnlyMixin


class TestAlgorithmTagLabel(TestCase):
    fixtures = ['test_algorithm_tags']
    view_name = 'get_algorithm_tag_label'

    def get_tag_labels(self, parameters):
        url = '{}?{}'.format(
            reverse(self.view_name), urllib.parse.urlencode(parameters)
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


@override_settings(PROBLEM_TAGS_VISIBLE=True)
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


@override_settings(PROBLEM_TAGS_VISIBLE=True)
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
        return self.url + '?' + urllib.parse.urlencode(parameters)

    @override_settings(LANGUAGE_CODE="en", PROBLEM_TAGS_VISIBLE=False)
    def test_search_no_hints_tags_basic(self):
        self.client.get('/c/c/')

        response = self.client.get(self.get_query_url({'q': 'najdłuższy'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'easy'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'Mediu'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'PROGRA'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'dYNAM'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'dp'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'increasing'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

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

    @override_settings(LANGUAGE_CODE="en", PROBLEM_TAGS_VISIBLE=False)
    def test_search_no_hints_origininfo(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'pa_'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.url, {'q': '2011'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.url, {'q': 'Round'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.url, {'q': 'Potyczki Algorytmiczne'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

    @override_settings(LANGUAGE_CODE="en")
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
