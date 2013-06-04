from datetime import datetime
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import utc

from oioioi.base.tests import fake_time
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contests.models import Contest
from oioioi.test_settings import MIDDLEWARE_CLASSES


class ContestIdViewCheckMixin(object):

    def _assertContestVisible(self, contest_id):
        response = self.client.get('/c/' + contest_id + '/id/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, contest_id)

    def _assertContestRedirects(self, contest_id, where):
        response = self.client.get('/c/' + contest_id + '/id/')
        self.assertEqual(response.status_code, 302)
        self.assertIn(where, response['Location'])


@override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES +
    ('oioioi.contestexcl.middleware.ExclusiveContestsMiddleware',))
class TestExclusiveContests(TestCase, ContestIdViewCheckMixin):
    urls = 'oioioi.contests.test_urls'
    fixtures = ['test_users', 'test_two_empty_contests']

    def setUp(self):
        self.c1 = Contest.objects.get(id='c1')
        self.c2 = Contest.objects.get(id='c2')

    def test_exclusive_contest(self):
        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        self.client.login(username='test_user')

        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        ex_conf = ExclusivenessConfig()
        ex_conf.contest = self.c2
        ex_conf.start_date = datetime(2012, 1, 1, 10, tzinfo=utc)
        ex_conf.end_date = datetime(2012, 1, 1, 14, tzinfo=utc)
        ex_conf.save()

        with fake_time(datetime(2012, 1, 1, 9, 59, tzinfo=utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 11, tzinfo=utc)):
            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 14, 1, tzinfo=utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

    def test_enabled_field(self):
        ex_conf = ExclusivenessConfig()
        ex_conf.contest = self.c2
        ex_conf.start_date = datetime(2012, 1, 1, 10, tzinfo=utc)
        ex_conf.end_date = datetime(2012, 1, 1, 14, tzinfo=utc)
        ex_conf.enabled = False
        ex_conf.save()

        with fake_time(datetime(2012, 1, 1, 11, tzinfo=utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

            ex_conf.enabled = True
            ex_conf.save()

            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

    def test_exclusive_contests_error(self):
        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        ex_conf = ExclusivenessConfig()
        ex_conf.contest = self.c1
        ex_conf.start_date = datetime(2012, 1, 1, 10, tzinfo=utc)
        ex_conf.end_date = datetime(2012, 1, 1, 14, tzinfo=utc)
        ex_conf.save()

        ex_conf = ExclusivenessConfig()
        ex_conf.contest = self.c2
        ex_conf.start_date = datetime(2012, 1, 1, 12, tzinfo=utc)
        ex_conf.end_date = datetime(2012, 1, 1, 16, tzinfo=utc)
        ex_conf.save()

        with fake_time(datetime(2012, 1, 1, 13, tzinfo=utc)):
            response = self.client.get('/c/c1/id/')
            self.assertContains(response,
                                'participate in more than one contest that exc')
            self.assertEqual(len(mail.outbox), 1)
            message = mail.outbox[0]
            self.assertEqual(list(message.to), ['admin@example.com'])
            self.assertIn('in more than one exclusive contest', message.body)
            self.assertIn('c1', message.body)
            self.assertIn('c2', message.body)

    def test_default_selector(self):
        self.client.login(username='test_admin')

        ex_conf = ExclusivenessConfig()
        ex_conf.contest = self.c1
        ex_conf.start_date = datetime(2012, 1, 1, 10, tzinfo=utc)
        ex_conf.end_date = datetime(2012, 1, 1, 14, tzinfo=utc)
        ex_conf.save()

        with fake_time(datetime(2012, 1, 1, 12, tzinfo=utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')
