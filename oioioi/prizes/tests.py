from collections import namedtuple
from contextlib import contextmanager
from datetime import timedelta  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import timezone

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.prizes.models import Prize, PrizeForUser, PrizeGiving
from oioioi.prizes.utils import FairAssignmentNotFound, assign_from_order
from oioioi.programs.controllers import ProgrammingContestController


def _single_prize_for_user(pg):
    test_user = User.objects.get(username='test_user')
    test_prize = pg.prize_set.all()[0]
    PrizeForUser(user=test_user, prize=test_prize).save()


def _prizes_by_user_id(pg):
    users = User.objects.all().order_by('id')
    assign_from_order(pg, enumerate(users))


def _with_conflict(pg):
    users = User.objects.all().order_by('id')[:2]
    assign_from_order(pg, [(1, user) for user in users])


class PrizesContestController(ProgrammingContestController):
    def get_prizes_distributors(self):
        return {'single': ('S', _single_prize_for_user),
                'by_id': ('B', _prizes_by_user_id),
                'conflict': ('C', _with_conflict)}

    def get_prizes_email_addresses(self, pg):
        return ['admin@example.com']


@contextmanager
def mock_sending_task():
    send_task = PrizeGiving._send_task_to_worker
    PrizeGiving._send_task_to_worker = lambda self: None
    yield
    PrizeGiving._send_task_to_worker = send_task


_create_PG = PrizeGiving.objects.create
_create_PR = Prize.objects.create


_future = timezone.now() + timedelta(days=700)
_past = timezone.now() - timedelta(days=200)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)
class TestPrizes(TestCase):
    fixtures = ['test_users', 'test_contest']

    # Note that prizes distribution in place leaves PrizeGiving instance
    # up-to-date whereas distribution by a remote worker doesn't,
    # so reload it if needed.

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
            'oioioi.prizes.tests.PrizesContestController'
        contest.save()
        self.assertTrue(self.client.login(username='test_user'))

    def test_menu(self):
        contest = Contest.objects.get()
        pg = _create_PG(contest=contest, name='PG', key='single')
        prize = _create_PR(contest=contest, prize_giving=pg, name='Prize',
                           quantity=2, order=10)

        dashboard_url = reverse('contest_dashboard',
                            kwargs={'contest_id': contest.id})
        prizes_url = reverse('default_prizes',
                            kwargs={'contest_id': contest.id})

        response = self.client.get(dashboard_url)
        self.assertNotIn(prizes_url.encode('utf-8'), response.content)
        response = self.client.get(prizes_url)
        self.assertEqual(403, response.status_code)

        test_user = User.objects.get(username='test_user')
        PrizeForUser(user=test_user, prize=prize).save()
        pg.state = 'SUCCESS'
        pg.save()

        response = self.client.get(dashboard_url)
        self.assertIn(prizes_url.encode('utf-8'), response.content)
        response = self.client.get(prizes_url)
        self.assertEqual(200, response.status_code)

    def test_prize_giving(self):
        contest = Contest.objects.get()
        pg = _create_PG(contest=contest, name='PG', key='single')
        pg.schedule()
        self.assertEqual('NOT_SCHEDULED', pg.state)

        _create_PR(contest=contest, prize_giving=pg, name='Prize1',
                   quantity=2, order=10)
        _create_PR(contest=contest, prize_giving=pg, name='Prize2',
                   quantity=1, order=8)

        pg.update(key='by_id', date=_future)
        pg.schedule()

        prizes_url = reverse('default_prizes',
                            kwargs={'contest_id': contest.id})

        response = self.client.get(prizes_url)
        pfus = response.context['pfus']
        pairs = [(pfu.user.id, pfu.prize.name) for pfu in pfus]
        self.assertEqual(
                pairs, [(1000, 'Prize2'), (1001, 'Prize1'), (1002, 'Prize1')])

    def test_tabs(self):
        contest = Contest.objects.get()
        pgl = [
                _create_PG(contest=contest, name='common', key='single',
                           date=_future),
                _create_PG(contest=contest, name='lonely', key='single',
                           date=_future),
                _create_PG(contest=contest, name='common', key='by_id',
                           date=_future + timedelta(days=1)),
        ]
        _create_PR(contest=contest, prize_giving=pgl[0], name='P0',
                   quantity=2, order=1)
        _create_PR(contest=contest, prize_giving=pgl[1], name='P1',
                   quantity=2, order=10)
        _create_PR(contest=contest, prize_giving=pgl[2], name='P2',
                   quantity=2, order=2)

        for pg in pgl:
            pg.schedule()  # Distribution is invoked by a remote worker.

        # Check against the database because states in pgl are out of date.
        self.assertEqual(
                PrizeGiving.objects.filter(state='SUCCESS').count(), 3)

        prizes_url = reverse('prizes',
                kwargs={'contest_id': contest.id, 'key': pgl[2].pk})

        response = self.client.get(prizes_url)
        self.assertEqual(200, response.status_code)
        self.assertIn('common', response.content)
        self.assertIn('lonely', response.content)
        groups = response.context['groups']
        Group = namedtuple('Group', 'name ids')
        self.assertEqual(groups, [
                Group(name='common', ids=[pgl[2].pk, pgl[0].pk]),
                Group(name='lonely', ids=[pgl[1].pk]),
        ])
        self.assertIn('P0', response.content)
        self.assertNotIn('P1', response.content)
        self.assertIn('P2', response.content)

        pfus = response.context['pfus']
        self.assertEqual([pfu.prize.name for pfu in pfus], ['P2', 'P2', 'P0'])

    def test_scheduling(self):
        contest = Contest.objects.get()
        pg = _create_PG(contest=contest, name='spam', key='by_id')
        prize = _create_PR(contest=contest, prize_giving=pg, name='Prize',
                           quantity=2, order=10)
        pg.schedule()
        self.assertEqual('NOT_SCHEDULED', pg.state)
        self.assertFalse(PrizeForUser.objects.exists())

        pg.update(date=_future)
        with mock_sending_task():
            pg.schedule()
        self.assertEqual('SCHEDULED', pg.state)
        self.assertFalse(PrizeForUser.objects.exists())

        pg.update(date=None, name='changed_when_scheduled')
        self.assertEqual('NOT_SCHEDULED', pg.state)

        pg.update(date=_past)
        pg.schedule()
        self.assertEqual('SUCCESS', pg.state)
        self.assertEqual(PrizeForUser.objects.count(), 2)

        prize.quantity = 1
        prize.save()
        pg.update(name='changed_after_success_with_no_reset', key='single')
        self.assertEqual('SUCCESS', pg.state)
        self.assertEqual(PrizeForUser.objects.count(), 2)
        pg.schedule()
        self.assertEqual('SUCCESS', pg.state)
        self.assertEqual(PrizeForUser.objects.count(), 2)
        self.assertIn('Prize', pg.report.read())

        pg.update(force_reset=True, name='brrr', date=_past)
        self.assertEqual('NOT_SCHEDULED', pg.state)
        self.assertFalse(PrizeForUser.objects.exists())
        self.assertEqual(None, pg.report)

        pg.schedule()
        self.assertEqual('SUCCESS', pg.state)
        self.assertEqual(PrizeForUser.objects.count(), 1)

    def test_failure_handling(self):
        contest = Contest.objects.get()
        pg = _create_PG(contest=contest, name='PG', key='conflict',
                        date=_past)
        _prize1 = _create_PR(contest=contest, prize_giving=pg, name='Prize1',
                            quantity=1, order=10)
        prize2 = _create_PR(contest=contest, prize_giving=pg, name='Prize2',
                            quantity=1, order=8)

        pg.schedule()
        self.assertEqual('FAILURE', pg.state)

        m = mail.outbox[0].message()

        self.assertIn("PG", m['Subject'])
        self.assertEqual("admin@example.com", m['To'])
        self.assertIn("no fair", m.as_string())
        self.assertIn("prizes_conflict.csv", m.as_string())

        self.assertIn('<<<', pg.report.read())

        prize2.delete()
        pg.update(force_reset=True, date=_past)
        pg.schedule()

        m = mail.outbox[1].message()
        self.assertIn("Nothing", m.as_string())

        self.assertFalse(PrizeForUser.objects.exists())

    def test_assign_from_order(self):
        contest = Contest.objects.get()
        pg = _create_PG(contest=contest, name='PG', key='by_id')

        assign_from_order(pg, [])
        assign_from_order(pg, enumerate(User.objects.all()))
        self.assertFalse(PrizeForUser.objects.exists())

        _create_PR(contest=contest, prize_giving=pg, name='Prize',
                   quantity=2, order=10)

        order = [(nr // 2, u) for nr, u in enumerate(User.objects.all())]
        assign_from_order(pg, order)
        self.assertEqual(2, PrizeForUser.objects.count())

        PrizeForUser.objects.all().delete()

        order = [(1, u) for u in User.objects.all()]
        with self.assertRaises(FairAssignmentNotFound):
            assign_from_order(pg, order)

        _create_PR(contest=contest, prize_giving=pg, name='Prize2',
                   quantity=100, order=11)

        with self.assertRaises(FairAssignmentNotFound):
            assign_from_order(pg, order)

        assign_from_order(pg, enumerate(User.objects.all()[:3]))
        self.assertEqual(3, PrizeForUser.objects.count())

    def test_version(self):
        contest = Contest.objects.get()
        pg = _create_PG(contest=contest, name='PG', date=_future, key='by_id')
        _create_PR(contest=contest, prize_giving=pg, name='Prize',
                   quantity=1, order=1)

        with mock_sending_task():
            version0 = pg.version
            pg.schedule()
            version1 = pg.version
            self.assertNotEqual(version0, version1)

            pg.update(name='yo yo', key='single')
            version2 = pg.version
            pg.schedule()  # ``pg`` is 'SCHEDULED' before call
            self.assertEqual(version1, version2)

            pg.update(date=_future + timedelta(days=3), name='ii', key='mwha')
            version3 = pg.version
            self.assertNotEqual(version2, version3)
            pg.schedule()

            pg.update(force_reset=True)
            version4 = pg.version
            self.assertNotEqual(version3, version4)
            pg.schedule()

        pg.update(date=None)
        version5 = pg.version
        self.assertNotEqual(version4, version5)

        pg.update(date=_past, key='single')
        version6 = pg.version
        pg.schedule()
        version7 = pg.version
        self.assertNotEqual(version6, version7)
