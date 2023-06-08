from datetime import datetime, timezone  # pylint: disable=E0611

from django.core import mail
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contests.models import Contest
from oioioi.test_settings import MIDDLEWARE


def add_ex_conf(contest, start_date, end_date=None, enabled=True):
    ex_conf = ExclusivenessConfig()
    ex_conf.contest = contest
    ex_conf.start_date = start_date
    ex_conf.end_date = end_date
    ex_conf.enabled = enabled
    ex_conf.save()
    return ex_conf


class ContestIdViewCheckMixin(object):
    def _assertContestVisible(self, contest_id):
        response = self.client.get('/c/' + contest_id + '/id/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), contest_id)

    def _assertContestRedirects(self, contest_id, where):
        response = self.client.get('/c/' + contest_id + '/id/')
        self.assertEqual(response.status_code, 302)
        self.assertIn(where, response['Location'])


@override_settings(
    MIDDLEWARE=MIDDLEWARE
    + ('oioioi.contestexcl.middleware.ExclusiveContestsMiddleware',),
    ROOT_URLCONF='oioioi.contests.tests.test_urls',
)
class TestExclusiveContestsAdmin(TestCase, ContestIdViewCheckMixin):
    fixtures = ['test_permissions', 'test_users', 'test_contest']

    def setUp(self):
        self.c = Contest.objects.get(id='c')

        self.user = Client()
        self.admin = Client()
        self.contestadmin = Client()

        self.user.login(username='test_user')
        self.admin.login(username='test_admin')
        self.contestadmin.login(username='test_contest_admin')

        self.url = reverse('admin:contests_contest_change', args=[self.c.id])

    def _check_user_access(self):
        response = self.user.get(self.url, follow=True)
        self.assertEqual(response.status_code, 403)

    def _check_contestadmin_access(self, visible):
        response = self.contestadmin.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        if visible:
            self.assertContains(response, 'Exclusiveness configs')
        else:
            self.assertNotContains(response, 'Exclusiveness configs')

    def _check_superadmin_access(self):
        response = self.admin.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Exclusiveness configs')

    def test_no_exclusiveness(self):
        self._check_user_access()
        self._check_contestadmin_access(visible=False)
        self._check_superadmin_access()

    def test_exclusiveness_on(self):
        add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
        )

        self._check_user_access()
        self._check_contestadmin_access(visible=True)
        self._check_superadmin_access()

    def test_exclusiveness_off(self):
        add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
            False,
        )

        self._check_user_access()
        self._check_contestadmin_access(visible=False)
        self._check_superadmin_access()

    def test_exclusiveness_multiple_on(self):
        add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
        )

        add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 12, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 16, tzinfo=timezone.utc),
        )
        self._check_user_access()
        self._check_contestadmin_access(visible=True)
        self._check_superadmin_access()

    def test_exclusiveness_multiple_off(self):
        add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
            False,
        )

        add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 12, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 16, tzinfo=timezone.utc),
            False,
        )
        self._check_user_access()
        self._check_contestadmin_access(visible=False)
        self._check_superadmin_access()

    def test_exclusiveness_multiple_mixed_on_off(self):
        ex_conf_1 = add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
        )

        ex_conf_2 = add_ex_conf(
            self.c,
            datetime(2012, 1, 1, 12, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 16, tzinfo=timezone.utc),
            False,
        )
        self._check_user_access()
        self._check_contestadmin_access(visible=True)
        self._check_superadmin_access()

        ex_conf_1.enabled = False
        ex_conf_1.save()
        ex_conf_2.enabled = True
        ex_conf_2.save()
        self._check_user_access()
        self._check_contestadmin_access(visible=True)
        self._check_superadmin_access()

    def _modify_contestexcl(
        self,
        round_start_date_form,
        round_end_date_form=('', ''),
        excl_start_date_forms=(),
        excl_end_date_forms=(),
    ):
        response = self.admin.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        formsets = (
            ('round_set', 1, 1, 0, 1000),
            ('c_attachments', 0, 0, 0, 1000),
            ('usergroupranking_set', 0, 0, 0, 1000),
            ('contestlink_set', 0, 0, 0, 1000),
            ('messagenotifierconfig_set', 0, 0, 0, 1000),
            ('mail_submission_config', 0, 0, 0, 1),
            ('prizegiving_set', 0, 0, 0, 1000),
            ('prize_set', 0, 0, 0, 1000),
            ('teamsconfig', 0, 0, 0, 1),
            ('problemstatementconfig', 0, 0, 0, 1),
            ('rankingvisibilityconfig', 0, 0, 0, 1),
            ('registrationavailabilityconfig', 0, 0, 0, 1),
            ('balloonsdeliveryaccessdata', 0, 0, 0, 1),
            ('statistics_config', 0, 0, 0, 1),
            ('exclusivenessconfig_set', len(excl_start_date_forms), 0, 0, 1000),
            ('complaints_config', 0, 0, 0, 1),
            ('disqualifications_config', 0, 0, 0, 1),
            ('contesticon_set', 0, 0, 0, 1000),
            ('contestlogo', 0, 0, 0, 1),
            ('programs_config', 0, 0, 0, 1),
            ('contestcompiler_set', 0, 0, 0, 1000),
        )
        data = dict()
        for (name, total, initial, min_num, max_num) in formsets:
            data.update(
                {
                    '{}-TOTAL_FORMS'.format(name): total,
                    '{}-INITIAL_FORMS'.format(name): initial,
                    '{}-MIN_NUM_FORMS'.format(name): min_num,
                    '{}-MAX_NUM_FORMS'.format(name): max_num,
                }
            )
        data.update(
            {
                'name': 'Contestexcl Test Contest',
                'start_date_0': '2000-01-01',
                'start_date_1': '00:00:00',
                'end_date_0': '',
                'end_date_1': '',
                'results_date_0': '',
                'results_date_1': '',
                'round_set-0-id': 1,
                'round_set-0-contest': 'c',
                'round_set-0-name': 'Contestexcl Test Round',
                'round_set-0-start_date_0': round_start_date_form[0],
                'round_set-0-start_date_1': round_start_date_form[1],
                'round_set-0-end_date_0': round_end_date_form[0],
                'round_set-0-end_date_1': round_end_date_form[1],
            }
        )
        for i in range(len(excl_start_date_forms)):
            data.update(
                {
                    'exclusivenessconfig_set-{}-id'.format(i): '',
                    'exclusivenessconfig_set-{}-contest'.format(i): 'c',
                    'exclusivenessconfig_set-{}-enabled'.format(i): 'on',
                    'exclusivenessconfig_set-{}-start_date_0'.format(
                        i
                    ): excl_start_date_forms[i][0],
                    'exclusivenessconfig_set-{}-start_date_1'.format(
                        i
                    ): excl_start_date_forms[i][1],
                    'exclusivenessconfig_set-{}-end_date_0'.format(i): '',
                    'exclusivenessconfig_set-{}-end_date_1'.format(i): '',
                }
            )
        for i in range(len(excl_end_date_forms)):
            data.update(
                {
                    'exclusivenessconfig_set-{}-end_date_0'.format(
                        i
                    ): excl_end_date_forms[i][0],
                    'exclusivenessconfig_set-{}-end_date_1'.format(
                        i
                    ): excl_end_date_forms[i][1],
                }
            )

        post_url = (
            reverse('oioioiadmin:contests_contest_change', args=[self.c.id])
            + '?simple=true'
        )
        response = self.admin.post(post_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        return response

    def test_exclusiveness_round_warning(self):
        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'), ('', ''), [('2019-01-01', '12:00:00')], []
        )
        self.assertContains(response, "is not exclusive from")

        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'), ('', ''), [('2019-01-01', '10:00:00')], []
        )
        self.assertNotContains(response, "is not exclusive from")

        for h in (7, 9, 11):
            response = self._modify_contestexcl(
                ('2019-01-01', '10:00:00'),
                ('', ''),
                [('2019-01-01', '{}:00:00'.format(h))],
                [('2019-01-01', '{}:00:00'.format(h + 2))],
            )
            self.assertContains(response, "is not exclusive from")

        for h in (6, 8, 10, 12, 14):
            response = self._modify_contestexcl(
                ('2019-01-01', '09:30:00'),
                ('2019-01-01', '12:30:00'),
                [('2019-01-01', '{}:00:00'.format(h))],
                [('2019-01-01', '{}:00:00'.format(h + 2))],
            )
            self.assertContains(response, "is not exclusive from")

        response = self._modify_contestexcl(
            ('2019-01-01', '10:30:00'),
            ('2019-01-01', '11:30:00'),
            [('2019-01-01', '10:00:00')],
            [('2019-01-01', '12:00:00')],
        )
        self.assertNotContains(response, "is not exclusive from")

    def test_exclusiveness_round_warning_multiple_configs(self):
        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'),
            ('', ''),
            [('2019-01-01', '13:00:00'), ('2019-01-01', '10:00:00')],
            [('', ''), ('2019-01-01', '12:00:00')],
        )
        self.assertContains(response, "is not exclusive from")

        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'),
            ('', ''),
            [('2019-01-01', '12:00:00'), ('2019-01-01', '10:00:00')],
            [('', ''), ('2019-01-01', '12:00:00')],
        )
        self.assertNotContains(response, "is not exclusive from")

        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'),
            ('2019-01-01', '15:00:00'),
            [
                ('2019-01-01', '13:00:00'),
                ('2019-01-01', '12:00:00'),
                ('2019-01-01', '11:00:00'),
                ('2019-01-01', '10:00:00'),
            ],
            [
                ('2019-01-01', '14:00:00'),
                ('2019-01-01', '13:00:00'),
                ('2019-01-01', '12:00:00'),
                ('2019-01-01', '11:00:00'),
            ],
        )
        self.assertContains(response, "is not exclusive from")

        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'),
            ('2019-01-01', '15:00:00'),
            [
                ('2019-01-01', '14:00:00'),
                ('2019-01-01', '13:00:00'),
                ('2019-01-01', '11:00:00'),
                ('2019-01-01', '10:00:00'),
            ],
            [
                ('2019-01-01', '15:00:00'),
                ('2019-01-01', '14:00:00'),
                ('2019-01-01', '12:00:00'),
                ('2019-01-01', '11:00:00'),
            ],
        )
        self.assertContains(response, "is not exclusive from")

        response = self._modify_contestexcl(
            ('2019-01-01', '10:00:00'),
            ('2019-01-01', '15:00:00'),
            [
                ('2019-01-01', '14:00:00'),
                ('2019-01-01', '12:00:00'),
                ('2019-01-01', '11:00:00'),
                ('2019-01-01', '10:00:00'),
            ],
            [
                ('2019-01-01', '15:00:00'),
                ('', ''),
                ('2019-01-01', '12:00:00'),
                ('2019-01-01', '11:00:00'),
            ],
        )
        self.assertNotContains(response, "is not exclusive from")


@override_settings(
    MIDDLEWARE=MIDDLEWARE
    + ('oioioi.contestexcl.middleware.ExclusiveContestsMiddleware',),
    ROOT_URLCONF='oioioi.contests.tests.test_urls',
)
class TestExclusiveContests(TestCase, ContestIdViewCheckMixin):
    fixtures = ['test_users', 'test_two_empty_contests']

    def setUp(self):
        self.c1 = Contest.objects.get(id='c1')
        self.c2 = Contest.objects.get(id='c2')

    def test_exclusive_contest(self):
        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        self.assertTrue(self.client.login(username='test_user'))

        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        add_ex_conf(
            self.c2,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
        )

        with fake_time(datetime(2012, 1, 1, 9, 59, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 11, tzinfo=timezone.utc)):
            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 14, 1, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

    def test_exclusive_contest_multiple_configs(self):
        add_ex_conf(
            self.c2,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 12, tzinfo=timezone.utc),
        )

        add_ex_conf(
            self.c2,
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 16, tzinfo=timezone.utc),
        )

        with fake_time(datetime(2012, 1, 1, 9, 59, 59, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 10, tzinfo=timezone.utc)):
            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 11, 59, 59, tzinfo=timezone.utc)):
            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 12, 0, 1, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 13, 59, 59, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 14, 0, 1, tzinfo=timezone.utc)):
            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 15, 59, 59, tzinfo=timezone.utc)):
            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

        with fake_time(datetime(2012, 1, 1, 16, 0, 1, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

    def test_enabled_field(self):
        ex_conf = add_ex_conf(
            self.c2,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
            False,
        )

        with fake_time(datetime(2012, 1, 1, 11, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')

            ex_conf.enabled = True
            ex_conf.save()

            self._assertContestRedirects('c1', '/c/c2/')
            self._assertContestVisible('c2')

    def test_exclusive_contests_error(self):
        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        add_ex_conf(
            self.c1,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
        )

        add_ex_conf(
            self.c2,
            datetime(2012, 1, 1, 12, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 16, tzinfo=timezone.utc),
        )

        with fake_time(datetime(2012, 1, 1, 13, tzinfo=timezone.utc)):
            response = self.client.get('/c/c1/id/')
            self.assertContains(
                response, 'participate in more than one contest that exc'
            )
            self.assertEqual(len(mail.outbox), 1)
            message = mail.outbox[0]
            self.assertEqual(list(message.to), ['admin@example.com'])
            self.assertIn('in more than one exclusive contest', message.body)
            self.assertIn('c1', message.body)
            self.assertIn('c2', message.body)

    def test_default_selector(self):
        self.assertTrue(self.client.login(username='test_admin'))

        add_ex_conf(
            self.c1,
            datetime(2012, 1, 1, 10, tzinfo=timezone.utc),
            datetime(2012, 1, 1, 14, tzinfo=timezone.utc),
        )

        with fake_time(datetime(2012, 1, 1, 12, tzinfo=timezone.utc)):
            self._assertContestVisible('c1')
            self._assertContestVisible('c2')
