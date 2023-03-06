import datetime

from django.urls import reverse

from oioioi.base.tests import TestCase, check_not_accessible
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import Contest, Round
from oioioi.timeline.views import _get_date_id


class TestTimelineView(TestCase):
    fixtures = [
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_extra_rounds',
        'test_users',
    ]

    def test_response(self):
        contest = Contest.objects.get()
        url = reverse('timeline_view', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, {'contest': contest})
        self.assertEqual(response.status_code, 200)

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            date = getattr(obj, item['date_field'])
            if date is not None:
                self.assertContains(response, date.strftime('%Y-%m-%d %H:%M'))

        for round in Round.objects.filter(contest=contest.id).values():
            self.assertContains(
                response, round['start_date'].strftime('%Y-%m-%d %H:%M')
            )

    def test_menu(self):
        contest = Contest.objects.get()

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertNotContains(response, 'Timeline')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertContains(response, 'Timeline')


class TestChangingDates(TestCase):
    fixtures = [
        'test_contest',
        'test_empty_package',
        'test_extra_rounds',
        'test_users',
        'test_permissions',
        'test_one_round_contest',
    ]

    # pylint: disable=dangerous-default-value
    def _send_post(
        self,
        contest=None,
        data={},
        user_code=403,
        admin_code=200,
        contest_admin_code=200,
        admin_assertin=None,
        admin_assertnotin=None,
    ):
        if contest is None:
            contest = Contest.objects.get(pk='c')

        url = reverse('timeline_view', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, user_code)

        admin_codes = {
            'test_contest_admin': contest_admin_code,
            'test_admin': admin_code,
        }

        for admin in admin_codes:
            self.assertTrue(self.client.login(username=admin))
            response = self.client.post(url, data=data)
            self.assertEqual(response.status_code, admin_codes[admin])

            if admin_assertin is not None:
                self.assertContains(
                    response, admin_assertin, status_code=admin_codes[admin]
                )

            if admin_assertnotin is not None:
                self.assertNotContains(
                    response, admin_assertnotin, status_code=admin_codes[admin]
                )

        return response

    def test_empty_post(self):
        self._send_post(admin_assertnotin='alert-danger')

    def test_valid_date_change(self):
        contest = Contest.objects.get(pk='c')
        delta = datetime.timedelta(days=21)
        new_dates = {}

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                new_date = (old_date + delta).strftime("%Y-%m-%d %H:%M")
                new_dates[_get_date_id(item)] = new_date

        response = self._send_post(
            contest, data=new_dates, admin_assertnotin='alert-danger'
        )

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            date = getattr(obj, item['date_field'])
            if date is not None:
                date = date.strftime("%Y-%m-%d %H:%M")
                self.assertEqual(date, new_dates[_get_date_id(item)])
                self.assertContains(response, date)

    def test_valid_unset_date_change(self):
        contest = Contest.objects.get(pk='c')
        unset_item = {'model': Round, 'id': 2, 'date_field': 'end_date'}
        new_date = '2021-10-10 10:10'
        unset_item_id = _get_date_id(unset_item)
        new_dates = {unset_item_id: new_date}

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                new_date = old_date.strftime("%Y-%m-%d %H:%M")
                new_dates[_get_date_id(item)] = new_date

        self._send_post(data=new_dates)

        obj = Round.objects.get(pk=2)
        self.assertEqual(
            obj.end_date, datetime.datetime(2021, 10, 10, 10, 10, tzinfo=datetime.timezone.utc)
        )

    def test_invalid_date_change(self):
        contest = Contest.objects.get(pk='c')
        delta = datetime.timedelta(days=55)
        new_dates = {}

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                new_date = (old_date - delta).strftime("%Y-%m-%d %H:%M")
                new_dates[_get_date_id(item)] = new_date

        invalid_item = {'model': Round, 'id': 3, 'date_field': 'start_date'}
        invalid_date = '2019-10-10 10:10'
        invalid_item_id = _get_date_id(invalid_item)
        new_dates[invalid_item_id] = invalid_date

        response = self._send_post(
            contest, data=new_dates, admin_assertin='alert-danger'
        )

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                new_date = new_dates[_get_date_id(item)]
                self.assertContains(response, new_date)
                self.assertNotEqual(new_date, old_date.strftime("%Y-%m-%d %H:%M"))

    def test_invalid_date_format(self):
        contest = Contest.objects.get(pk='c')
        delta = datetime.timedelta(days=13)
        new_dates = {}

        for item in date_registry.tolist(contest.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                new_date = (old_date + delta).strftime("%d/%m/%Y %H:%M")
                new_dates[_get_date_id(item)] = new_date

        self._send_post(
            contest, data=new_dates, admin_assertin='Date format is invalid'
        )

    def test_changing_date_in_wrong_contest(self):
        contest_c = Contest.objects.get(pk='c')
        contest_d = Contest.objects.get(pk='d')
        delta = datetime.timedelta(days=13)
        new_dates = {}

        for item in date_registry.tolist(contest_c.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                new_date = (old_date + delta).strftime("%d/%m/%Y %H:%M")
                new_dates[_get_date_id(item)] = new_date

        self._send_post(contest_d, data=new_dates, contest_admin_code=403)

        for item in date_registry.tolist(contest_c.id):
            obj = item['model'].objects.get(pk=item['id'])
            old_date = getattr(obj, item['date_field'])
            if old_date is not None:
                old_date = old_date.strftime("%d/%m/%Y %H:%M")
                self.assertNotEqual(old_date, new_dates[_get_date_id(item)])
