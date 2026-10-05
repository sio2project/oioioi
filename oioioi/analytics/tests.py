from django.test.utils import override_settings

from oioioi.base.tests import TestCase


class TestAnalytics(TestCase):
    def test_without_analytics(self):
        response = self.client.get("/", follow=True)
        self.assertNotContains(response, "google-analytics.com")

    @override_settings(GOOGLE_ANALYTICS_TRACKING_ID="ga-tracking-id")
    def test_with_analytics(self):
        response = self.client.get("/", follow=True)
        self.assertContains(response, "google-analytics.com")
        self.assertContains(response, "ga-tracking-id")
