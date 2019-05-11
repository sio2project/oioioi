from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase


class TestSubmitService(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_messages', 'test_templates',
                'test_submitservice']

    def test_submit(self):
        ufile = SimpleUploadedFile('file.cpp', "int main() {}")
        url = reverse('submitservice_submit', kwargs={'contest_id': 'c'})
        response = self.client.post(url, {
            'file': ufile,
            'task': 'zad1',
            'token': '123456ABCDEF'
        })
        response_data = response.json()
        self.assertRegexpMatches(response_data['result_url'], r'\/c\/c\/s\/[0-9]+\/')

    def test_view_user_token(self):
        url = reverse('submitservice_view_user_token',
                      kwargs={'contest_id': 'c'})
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertContains(response, '123456ABCDEF')

    def test_clear_user_token(self):
        url = reverse('submitservice_clear_user_token',
                      kwargs={'contest_id': 'c'})
        self.assertTrue(self.client.login(username='test_user'))
        self.client.post(url)
        url = reverse('submitservice_view_user_token',
                      kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertNotContains(response, '123456ABCDEF')
