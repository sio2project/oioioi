import json

from oioioi.base.tests import TestCase
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile


class TestSubmitService(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_messages', 'test_templates',
                'test_submitservice']

    def test_submit(self):
        ufile = SimpleUploadedFile('file.cpp', "int main() {}")
        url = reverse('oioioi.submitservice.views.submit_view',
                      kwargs={'contest_id': 'c'})
        response = self.client.post(url, {
            'file': ufile,
            'task': 'zad1',
            'token': '123456ABCDEF'
        })
        response_data = json.loads(response.content)
        self.assertEqual(response_data['result_url'], '/c/c/s/1/')

    def test_view_user_token(self):
        url = reverse('oioioi.submitservice.views.view_user_token',
                      kwargs={'contest_id': 'c'})
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertIn('123456ABCDEF', response.content)

    def test_clear_user_token(self):
        url = reverse('oioioi.submitservice.views.clear_user_token',
                      kwargs={'contest_id': 'c'})
        self.client.login(username='test_user')
        self.client.post(url)
        url = reverse('oioioi.submitservice.views.view_user_token',
                      kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertNotIn('123456ABCDEF', response.content)
