from django.urls import reverse, resolve

from oioioi.base.tests import TestCase


class TestNewsfeedVisibility(TestCase):
    fixtures = ['test_users', 'newsfeed']

    def test_newsfeed_visibility(self):
        url_newsfeed = reverse('newsfeed')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test news')

    def test_newsfeed_options_visibility(self):
        url_newsfeed = reverse('newsfeed')
        url_add_news = reverse('add_news')
        url_edit_news = reverse('edit_news', kwargs={'news_id': 1})
        url_delete_news = reverse('delete_news', kwargs={'news_id': 1})

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        # superuser can see all newsfeed options
        self.assertContains(response, str(url_add_news))
        self.assertContains(response, str(url_edit_news))
        self.assertContains(response, str(url_delete_news))

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        # non-superuser cannot see any newsfeed options
        self.assertNotContains(response, str(url_add_news))
        self.assertNotContains(response, str(url_edit_news))
        self.assertNotContains(response, str(url_delete_news))


class TestNewsfeedPermissions(TestCase):
    fixtures = ['test_users', 'newsfeed']

    def test_add_permissions(self):
        url_add_news = reverse('add_news')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_add_news)
        # superuser can add news
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url_add_news)
        # non-superuser cannot add news
        self.assertEqual(response.status_code, 403)

    def test_edit_permissions(self):
        url_edit_news = reverse('edit_news', kwargs={'news_id': 1})

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_edit_news)
        # superuser can edit news
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url_edit_news)
        # non-superuser cannot edit news
        self.assertEqual(response.status_code, 403)

    def test_delete_permissions(self):
        url_delete_news = reverse('delete_news', kwargs={'news_id': 1})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url_delete_news)
        # non-superuser cannot delete news
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_delete_news, follow=True)
        # superuser can delete news
        self.assertEqual(response.status_code, 200)


class TestNewsfeedOptions(TestCase):
    fixtures = ['test_users', 'newsfeed']

    def _assert_redirect_to_newsfeed(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            resolve(response.redirect_chain[-1][0]).view_name,
            'newsfeed'
        )

    def test_news_add(self):
        url_newsfeed = reverse('newsfeed')
        url_add_news = reverse('add_news')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test news')
        self.assertNotContains(response, 'Testing add')
        response = self.client.get(url_add_news)
        self.assertEqual(response.status_code, 200)
        post_data = {
            'form-0-id': '',
            'form-0-title': 'Testing add',
            'form-0-content': 'Add tested',
            'form-0-language': 'en',
            'form-MAX_NUM_FORMS': 1,
            'form-TOTAL_FORMS': 1,
            'form-MIN_NUM_FORMS': 1,
            'form-INITIAL_FORMS': 0,
        }
        response = self.client.post(url_add_news, post_data, follow=True)
        self._assert_redirect_to_newsfeed(response)
        self.assertContains(response, 'Test news')
        self.assertContains(response, 'Testing add')

    def test_news_edit(self):
        url_newsfeed = reverse('newsfeed')
        url_edit_news = reverse('edit_news', kwargs={'news_id': 1})

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test news')
        self.assertNotContains(response, 'Test edited news')
        response = self.client.get(url_edit_news)
        self.assertEqual(response.status_code, 200)
        post_data = {
            'form-0-id': '1',
            'form-0-title': 'Test edited news',
            'form-0-content': 'This is a test',
            'form-0-language': 'en',
            'form-MAX_NUM_FORMS': 1,
            'form-TOTAL_FORMS': 1,
            'form-MIN_NUM_FORMS': 1,
            'form-INITIAL_FORMS': 1,
        }
        response = self.client.post(url_edit_news, post_data, follow=True)
        self._assert_redirect_to_newsfeed(response)
        self.assertContains(response, 'Test edited news')
        self.assertNotContains(response, 'Test news')

    def test_news_delete(self):
        url_newsfeed = reverse('newsfeed')
        url_delete_news = reverse('delete_news', kwargs={'news_id': 1})

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test news')
        response = self.client.get(url_delete_news, follow=True)
        self._assert_redirect_to_newsfeed(response)
        self.assertNotContains(response, 'Test news')
