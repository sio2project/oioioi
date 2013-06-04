from django.test import TestCase
from django.test.utils import override_settings


class TestAnalytics(TestCase):
    def test_without_analytics(self):
        response = self.client.get('/', follow=True)
        self.assertNotIn('google-analytics.com', response.content)

    @override_settings(GOOGLE_ANALYTICS_TRACKING_ID='ga-tracking-id')
    def test_with_analytics(self):
        response = self.client.get('/', follow=True)
        self.assertIn('google-analytics.com', response.content)
        self.assertIn('ga-tracking-id', response.content)
