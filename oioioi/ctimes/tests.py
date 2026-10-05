from datetime import UTC, datetime  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, Round, RoundTimeExtension


class TestCtimes(TestCase):
    fixtures = ["test_users", "test_two_empty_contests"]

    def setUp(self):
        contest1 = Contest.objects.get(id="c1")
        contest2 = Contest.objects.get(id="c2")
        rounds = [
            Round(
                name="round1",
                contest=contest1,
                start_date=datetime(2013, 10, 11, 8, 0, tzinfo=UTC),
                end_date=datetime(2013, 12, 5, 9, 0, tzinfo=UTC),
            ),
            Round(
                name="round2",
                contest=contest1,
                start_date=datetime(2013, 10, 22, 10, 0, tzinfo=UTC),
                end_date=datetime(2013, 11, 5, 11, 0, tzinfo=UTC),
            ),
            Round(
                name="round3",
                contest=contest1,
                start_date=datetime(2014, 1, 1, 1, 0, tzinfo=UTC),
                end_date=datetime(2014, 1, 1, 2, 0, tzinfo=UTC),
            ),
            # Starts 7 minutes after round3 ends.
            Round(
                name="round4",
                contest=contest1,
                start_date=datetime(2014, 1, 1, 2, 7, tzinfo=UTC),
                end_date=None,
            ),
            # For testing comparisons with rounds without ends
            # and between recently-ended rounds.
            Round(
                name="round5",
                contest=contest1,
                start_date=datetime(2015, 1, 1, tzinfo=UTC),
                end_date=datetime(2016, 1, 1, tzinfo=UTC),
            ),
            Round(
                name="round6",
                contest=contest1,
                start_date=datetime(2015, 1, 1, tzinfo=UTC),
                end_date=datetime(2016, 1, 1, 0, 0, 1, tzinfo=UTC),
            ),
            Round(
                name="round7",
                contest=contest1,
                start_date=datetime(2015, 1, 2, tzinfo=UTC),
                end_date=datetime(2016, 1, 1, tzinfo=UTC),
            ),
            Round(
                name="round1p",
                contest=contest2,
                start_date=datetime(2014, 1, 2, 3, 10, tzinfo=UTC),
                end_date=None,
            ),
        ]
        self.round1_result = {
            "status": "OK",
            "round_name": "round1",
            "start": "2013-10-11 08:00:00",
            "start_sec": 1381478400,
            "end": "2013-12-05 09:00:00",
            "end_sec": 1386234000,
        }
        self.round2_result = {
            "status": "OK",
            "round_name": "round2",
            "start": "2013-10-22 10:00:00",
            "start_sec": 1382436000,
            "end": "2013-11-05 11:00:00",
            "end_sec": 1383649200,
        }
        self.round3_result = {
            "status": "OK",
            "round_name": "round3",
            "start": "2014-01-01 01:00:00",
            "start_sec": 1388538000,
            "end": "2014-01-01 02:00:00",
            "end_sec": 1388541600,
        }
        self.round4_result = {
            "status": "OK",
            "round_name": "round4",
            "start": "2014-01-01 02:07:00",
            "start_sec": 1388542020,
            "end": None,
            "end_sec": None,
        }
        self.round5_result = {
            "status": "OK",
            "round_name": "round5",
            "start": "2015-01-01 00:00:00",
            "start_sec": 1420070400,
            "end": "2016-01-01 00:00:00",
            "end_sec": 1451606400,
        }
        self.round6_result = {
            "status": "OK",
            "round_name": "round6",
            "start": "2015-01-01 00:00:00",
            "start_sec": 1420070400,
            "end": "2016-01-01 00:00:01",
            "end_sec": 1451606401,
        }
        self.round7_result = {
            "status": "OK",
            "round_name": "round7",
            "start": "2015-01-02 00:00:00",
            "start_sec": 1420156800,
            "end": "2016-01-01 00:00:00",
            "end_sec": 1451606400,
        }
        self.round1p_result = {
            "status": "OK",
            "round_name": "round1p",
            "start": "2014-01-02 03:10:00",
            "start_sec": 1388632200,
            "end": None,
            "end_sec": None,
        }
        Round.objects.bulk_create(rounds)
        self.assertTrue(self.client.login(username="test_user"))

    def verify_result(self, url, result):
        response = self.client.get(url).json()
        self.assertEqual(response, result)

    def test_ctimes_order(self):
        url = reverse("ctimes", kwargs={"contest_id": "c1"})
        self.client.get(url)
        with fake_time(datetime(2013, 10, 1, 21, tzinfo=UTC)):
            self.verify_result(url, self.round1_result)
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=UTC)):
            self.verify_result(url, self.round1_result)
        with fake_time(datetime(2013, 10, 22, 9, 56, tzinfo=UTC)):
            self.verify_result(url, self.round1_result)
        with fake_time(datetime(2013, 10, 22, 10, tzinfo=UTC)):
            self.verify_result(url, self.round2_result)
        with fake_time(datetime(2013, 11, 5, 11, 1, tzinfo=UTC)):
            self.verify_result(url, self.round1_result)
        # Just after round2 ends:
        with fake_time(datetime(2013, 12, 5, 9, 1, tzinfo=UTC)):
            self.verify_result(url, self.round1_result)
        with fake_time(datetime(2013, 12, 5, 9, 5, tzinfo=UTC)):
            self.verify_result(url, self.round1_result)
        with fake_time(datetime(2013, 12, 5, 9, 6, tzinfo=UTC)):
            self.verify_result(url, self.round3_result)
        with fake_time(datetime(2014, 1, 1, 0, 1, tzinfo=UTC)):
            self.verify_result(url, self.round3_result)
        with fake_time(datetime(2014, 1, 1, 1, 0, tzinfo=UTC)):
            self.verify_result(url, self.round3_result)
        with fake_time(datetime(2014, 1, 1, 2, 1, tzinfo=UTC)):
            self.verify_result(url, self.round3_result)
        # Round3 just ended, but round4 starts in 5 minutes.
        with fake_time(datetime(2014, 1, 1, 2, 2, tzinfo=UTC)):
            self.verify_result(url, self.round4_result)
        with fake_time(datetime(2014, 1, 1, 2, 30, tzinfo=UTC)):
            self.verify_result(url, self.round4_result)
        # Since round4 is ongoing, no info about round5 should be shown.
        with fake_time(datetime(2014, 12, 31, 23, 59, 59, tzinfo=UTC)):
            self.verify_result(url, self.round4_result)
        # Rounds 5-6 just started. They end earlier than round4,
        # round5 ends a second earlier than round6.
        with fake_time(datetime(2015, 1, 1, 0, tzinfo=UTC)):
            self.verify_result(url, self.round5_result)
        Round.objects.get(name="round4").delete()
        with fake_time(datetime(2014, 1, 1, 2, 5, tzinfo=UTC)):
            self.verify_result(url, self.round3_result)
        # Rounds 5-7 just ended, but round6 did so a second later.
        with fake_time(datetime(2016, 1, 1, 0, 1, tzinfo=UTC)):
            self.verify_result(url, self.round6_result)
        with fake_time(datetime(2016, 1, 1, 1, tzinfo=UTC)):
            response = self.client.get(url).json()
            self.assertEqual(response["status"], "NO_ROUND")
        Contest.objects.all().delete()
        self.client.get("/")  # removes current contest
        url = reverse("ctimes")
        with fake_time(datetime(2013, 12, 11, 5, 0, tzinfo=UTC)):
            response = self.client.get(url).json()
            self.assertEqual(response["status"], "NO_CONTEST")

    def test_ctimes_format(self):
        url = reverse("ctimes", kwargs={"contest_id": "c1"})
        date_regexp = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
        with fake_time(datetime(2013, 10, 1, 21, tzinfo=UTC)):
            response = self.client.get(url).json()
            print(response)
            self.assertRegex(response["start"], date_regexp)
            self.assertRegex(response["end"], date_regexp)

    def test_ctimes_with_roundextension(self):
        url = reverse("ctimes", kwargs={"contest_id": "c1"})
        rnd = Round.objects.get(name="round1")
        user = User.objects.get(username="test_user")
        RoundTimeExtension.objects.create(round=rnd, user=user, extra_time=5)
        Round.objects.exclude(name="round1").delete()
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=UTC)):
            response = self.client.get(url).json()
            self.assertEqual(
                response,
                {
                    "status": "OK",
                    "round_name": "round1",
                    "start": "2013-10-11 08:00:00",
                    "start_sec": 1381478400,
                    "end": "2013-12-05 09:05:00",
                    "end_sec": 1386234300,
                },
            )

    def test_ctimes_anonymous(self):
        url = reverse("ctimes", kwargs={"contest_id": "c2"})
        self.client.logout()
        with fake_time(datetime(2014, 1, 2, 4, 56, tzinfo=UTC)):
            response = self.client.get(url).json()
            self.assertEqual(response, self.round1p_result)

    def test_ctimes_no_contest_id(self):
        url = reverse("ctimes")
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=UTC)):
            response = self.client.get(url, follow=True).json()
            self.assertEqual(response, self.round1p_result)

    def test_ctimes_no_end(self):
        url = reverse("ctimes", kwargs={"contest_id": "c2"})
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=UTC)):
            response = self.client.get(url).json()
            self.assertEqual(response, self.round1p_result)

    def test_cross_origin(self):
        url = reverse("ctimes", kwargs={"contest_id": "c2"})
        response = self.client.get(url)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
