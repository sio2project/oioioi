from django.core.urlresolvers import reverse
from django.test import TestCase


class TestNewsfeedVisibility(TestCase):
    fixtures = ['test_users', 'newsfeed']

    def test_newsfeed_visibility(self):
        url_newsfeed = reverse('newsfeed')

        self.client.login(username='test_admin')
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test news', response.content)

    def test_newsfeed_options_visibility(self):
        url_newsfeed = reverse('newsfeed')
        url_add_news = reverse('add_news')
        url_edit_news = reverse('edit_news', kwargs={'news_id': 1})
        url_delete_news = reverse('delete_news', kwargs={'news_id': 1})

        self.client.login(username='test_admin')
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        # superuser can see all newsfeed options
        self.assertIn(str(url_add_news), response.content)
        self.assertIn(str(url_edit_news), response.content)
        self.assertIn(str(url_delete_news), response.content)

        self.client.login(username='test_user')
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        # non-superuser cannot see any newsfeed options
        self.assertNotIn(str(url_add_news), response.content)
        self.assertNotIn(str(url_edit_news), response.content)
        self.assertNotIn(str(url_delete_news), response.content)


class TestNewsfeedPermissions(TestCase):
    fixtures = ['test_users', 'newsfeed']

    def test_add_permissions(self):
        url_add_news = reverse('add_news')

        self.client.login(username='test_admin')
        response = self.client.get(url_add_news)
        # superuser can add news
        self.assertEqual(response.status_code, 200)

        self.client.login(username='test_user')
        response = self.client.get(url_add_news)
        # non-superuser cannot add news
        self.assertEqual(response.status_code, 403)

    def test_edit_permissions(self):
        url_edit_news = reverse('edit_news', kwargs={'news_id': 1})

        self.client.login(username='test_admin')
        response = self.client.get(url_edit_news)
        # superuser can edit news
        self.assertEqual(response.status_code, 200)

        self.client.login(username='test_user')
        response = self.client.get(url_edit_news)
        # non-superuser cannot edit news
        self.assertEqual(response.status_code, 403)

    def test_delete_permissions(self):
        url_delete_news = reverse('delete_news', kwargs={'news_id': 1})

        self.client.login(username='test_user')
        response = self.client.get(url_delete_news)
        # non-superuser cannot delete news
        self.assertEqual(response.status_code, 403)

        self.client.login(username='test_admin')
        response = self.client.get(url_delete_news, follow=True)
        # superuser can delete news
        self.assertEqual(response.status_code, 200)


class TestNewsfeedOptions(TestCase):
    fixtures = ['test_users', 'newsfeed']

    def test_news_add(self):
        url_newsfeed = reverse('newsfeed')
        url_add_news = reverse('add_news')

        self.client.login(username='test_admin')
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Testing add', response.content)
        response = self.client.get(url_add_news)
        self.assertEqual(response.status_code, 200)
        post_data = {
            'title': 'Testing add',
            'content': 'Add tested'
        }
        response = self.client.post(url_add_news, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Testing add', response.content)

    def test_news_edit(self):
        url_newsfeed = reverse('newsfeed')
        url_edit_news = reverse('edit_news', kwargs={'news_id': 1})

        self.client.login(username='test_admin')
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test news', response.content)
        self.assertNotIn('Test edited news', response.content)
        response = self.client.get(url_edit_news)
        self.assertEqual(response.status_code, 200)
        post_data = {
            'title': 'Test edited news',
            'content': 'This is a test'
        }
        response = self.client.post(url_edit_news, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test edited news', response.content)
        self.assertNotIn('Test news', response.content)

    def test_news_delete(self):
        url_newsfeed = reverse('newsfeed')
        url_delete_news = reverse('delete_news', kwargs={'news_id': 1})

        self.client.login(username='test_admin')
        response = self.client.get(url_newsfeed)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test news', response.content)
        response = self.client.get(url_delete_news, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Test news', response.content)
