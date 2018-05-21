from django.test.utils import override_settings

from oioioi.base.tests import TestCase


class TestAnalytics(TestCase):
    def test_without_analytics(self):
        response = self.client.get('/', follow=True)
        self.assertNotIn(b'google-analytics.com', response.content)

    @override_settings(GOOGLE_ANALYTICS_TRACKING_ID='ga-tracking-id')
    def test_with_analytics(self):
        response = self.client.get('/', follow=True)
        self.assertIn(b'google-analytics.com', response.content)
        self.assertIn(b'ga-tracking-id', response.content)
