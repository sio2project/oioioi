# coding: utf-8

from django.urls import reverse

from oioioi.base.tests import TestCase, check_not_accessible
from oioioi.similarsubmits.forms import BulkAddSubmissionsSimilarityForm
from oioioi.similarsubmits.models import SubmissionsSimilarityGroup


def none_returner():
    return None


class TestSimilarSubmitViews(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_similarsubmits_extra_data',
    ]

    def test_bulk_add_similar_submits_view(self):
        # superuser
        self.assertTrue(self.client.login(username='test_admin'))

        url = reverse('bulk_add_similarities', kwargs={'contest_id': 'c'})
        groups = SubmissionsSimilarityGroup.objects.all()
        self.assertEqual(len(groups), 0)

        submissions_unions = [
            (
                (
                    '1:test_user:zad1.cpp 2:test_user2:zad1.cpp\n'
                    '3:test_user3:zad1.cpp 4:test_user4:zad1.cpp'
                ),
                2,
            ),
            ('1:test_user:zad1.cpp 2:test_user2:zad1.cpp\n', 2),
            ('2:test_user2:zad1.cpp 3:test_user3:zad1.cpp', 1),
        ]

        for sim_groups_str, sim_groups_cnt in submissions_unions:
            post_data = {
                'similar_groups': sim_groups_str,
            }
            response = self.client.post(url, post_data, follow=True)
            self.assertEqual(response.status_code, 200)

            groups = SubmissionsSimilarityGroup.objects.all()
            self.assertEqual(len(groups), sim_groups_cnt)

    def test_invalid_bulk_form(self):
        invalid_bulks = ['1:user:test.cpp', '1:usertestcpp 1:user:test.cpp']
        mock_request = none_returner
        mock_request.contest = None
        for bulk in invalid_bulks:
            form_data = {'similar_groups': bulk}
            form = BulkAddSubmissionsSimilarityForm(mock_request, data=form_data)
            self.assertFalse(form.is_valid())

    def test_permissions(self):
        url = reverse('bulk_add_similarities', kwargs={'contest_id': 'c'})

        # test anonymous
        self.client.logout()
        check_not_accessible(self, url)

        # normal user
        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url)
