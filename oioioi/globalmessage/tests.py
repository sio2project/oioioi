from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from oioioi.base.tests import TestCase
from oioioi.globalmessage.models import GlobalMessage


class TestVisible(TestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_visibility_dates(self):
        day = timezone.timedelta(days=1)

        tomorrow = self.now + day
        yesterday = self.now - day

        tests = (
            (None, None, True, 'test_no_dates'),
            (tomorrow, None, False, 'test_start_in_future'),
            (yesterday, None, True, 'test_start_in_past'),
            (None, tomorrow, True, 'test_end_in_future'),
            (None, yesterday, False, 'test_end_in_past'),
            (yesterday, tomorrow, True, 'test_start_past_end_future'),
            (yesterday - day, yesterday, False, 'test_start_past_end_past'),
            (tomorrow, tomorrow + day, False, 'test_start_future_end_future')
        )

        for test in tests:
            self.check_dates(*test)

    def check_dates(self, start, end, expected, desc):
        msg = GlobalMessage(
            message='Test',
            enabled=True,
            start=start,
            end=end,
        )

        actual = msg.visible(self.now)

        self.assertEqual(actual, expected, desc)

    def test_disabled(self):
        msg = GlobalMessage(
            message='Test',
            enabled=False,
            start=None,
            end=None,
        )

        self.assertFalse(msg.visible(self.now))


class TestOnPage(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.msg = GlobalMessage.get_singleton()

        self.msg.message = 'Example global message'
        self.msg.enabled = True

        self.msg.save()

    @override_settings(DEFAULT_GLOBAL_PORTAL_AS_MAIN_PAGE=False)
    def test_visible_on_user_pages(self):
        url = reverse('index')

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertContains(response, self.msg.message)

    def test_visible_on_admin_pages(self):
        url = reverse('admin:index')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertContains(response, self.msg.message)
