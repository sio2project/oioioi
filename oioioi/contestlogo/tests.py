import calendar

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.utils.http import http_date
from django.utils.timezone import timedelta

from oioioi.base.tests import TestCase
from oioioi.contestlogo.models import ContestIcon, ContestLogo
from oioioi.contests.models import Contest
from oioioi.programs.controllers import ProgrammingContestController


class ContestControllerWithoutDefaults(ProgrammingContestController):
    def default_contestlogo_url(self):
        return None

    def default_contesticons_urls(self):
        return []


class ContestControllerWithDefaults(ProgrammingContestController):
    def default_contestlogo_url(self):
        return '/some/URL/'

    def default_contesticons_urls(self):
        return ['/another/URL/']


class TestProcessorsWithoutUploadedFiles(TestCase):
    fixtures = ['test_users', 'test_contest']

    def _render_menu(self):
        user = User.objects.get(username='test_user')
        self.assertTrue(self.client.login(username=user))
        return self.client.get(reverse('index'), follow=True).content.decode('utf-8')

    def test_without_defaults(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.contestlogo.tests.ContestControllerWithoutDefaults'
        )
        contest.save()
        response = self._render_menu()
        self.assertNotIn('class="contesticon"', response)

    def test_with_defaults(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.contestlogo.tests.ContestControllerWithDefaults'
        )
        contest.save()
        response = self._render_menu()
        self.assertIn('/some/URL/', response)

        self.assertIn('class="contesticon"', response)
        self.assertIn('/another/URL/', response)


class TestProcessorsWithUploadedFiles(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_logo', 'test_icon']

    def _render_menu(self):
        user = User.objects.get(username='test_user')
        self.assertTrue(self.client.login(username=user))
        return self.client.get(reverse('index'), follow=True).content.decode('utf-8')

    def test_with_defauts_and_uploaded_files(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.contestlogo.tests.ContestControllerWithDefaults'
        )
        contest.save()
        response = self._render_menu()
        self.assertNotIn('/some/URL/', response)
        self.assertIn('/c/c/logo/', response)

        self.assertIn('class="contesticon"', response)
        self.assertNotIn('/another/URL/', response)
        self.assertIn('/c/c/icons/', response)


class TestUpdatedAt(TestCase):
    fixtures = ['test_contest', 'test_logo', 'test_icon']

    def to_http_date(self, dt):
        return http_date(calendar.timegm(dt.utctimetuple()))

    def request_file(self, url, update_date):
        date_before = self.to_http_date(update_date - timedelta(days=10))
        date_after = self.to_http_date(update_date + timedelta(days=10))

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = date_before
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.defaults['HTTP_IF_MODIFIED_SINCE'] = date_after
        response = self.client.get(url)
        self.assertEqual(response.status_code, 304)

    def test_icon_last_modified(self):
        icon = ContestIcon.objects.get()
        icon.image = ContentFile(b'eloziom', name='foo')
        icon.save()
        self.request_file('/c/c/icons/%d/' % icon.pk, icon.updated_at)

    def test_logo_last_modified(self):
        logo = ContestLogo.objects.get()
        logo.image = ContentFile(b'eloziom', name='foo')
        logo.save()
        self.request_file('/c/c/logo/', logo.updated_at)
