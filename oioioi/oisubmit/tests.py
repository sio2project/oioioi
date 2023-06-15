from datetime import datetime, timedelta, timezone  # pylint: disable=E0611

from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils.timezone import get_current_timezone

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, ProblemInstance, Round, Submission
from oioioi.oisubmit.err_dict import INCORRECT_FORM_COMMENTS, SUSPICION_REASONS
from oioioi.test_settings import OISUBMIT_MAGICKEY


class OISubmitFileMixin(object):
    def submit_file(
        self,
        contest,
        pi_short_name,
        localtime=None,
        siotime=None,
        magickey="",
        file_size=1024,
        file_name='submission.cpp',
    ):
        url = reverse('oisubmit', kwargs={'contest_id': contest.id})
        file = ContentFile('a' * file_size, name=file_name)

        if localtime is None:
            localtime = datetime.now(timezone.utc)

        if isinstance(localtime, datetime):
            localtime_str = localtime.astimezone(get_current_timezone()).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            localtime_str = localtime

        if not magickey:
            magickey = str(OISUBMIT_MAGICKEY)

        if siotime is None:
            siotime_str = ""
        elif isinstance(siotime, datetime):
            siotime_str = siotime.astimezone(get_current_timezone()).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            siotime_str = siotime

        post_data = {
            'localtime': localtime_str,
            'siotime': siotime_str,
            'magickey': magickey,
            'problem_shortname': pi_short_name,
            'pi_id': str(0),
            'file': file,
        }
        return self.client.post(url, post_data)

    def _assertSubmitted(self, response, submission_number):
        self.assertEqual(200, response.status_code)
        self.assertEqual(submission_number + 1, Submission.objects.all().count())

    def _assertNotSubmitted(self, response, submission_number):
        self.assertEqual(200, response.status_code)
        self.assertEqual(submission_number, Submission.objects.all().count())

    def _assertSuspected(self, response, submission_number, suspected_number, reason):
        self._assertSubmitted(response, submission_number)
        self.assertEqual(True, response.json()['error_occured'])
        self.assertIn(reason, response.json()['comment'])
        self.assertEqual(
            suspected_number + 1, Submission.objects.filter(kind='SUSPECTED').count()
        )

    def _assertNotSuspected(self, response, submission_number, suspected_number):
        self._assertSubmitted(response, submission_number)
        self.assertEqual(False, response.json()['error_occured'])
        self.assertEqual(
            suspected_number, Submission.objects.filter(kind='SUSPECTED').count()
        )

    def _assertFormError(self, response, submission_number, error):
        self._assertNotSubmitted(response, submission_number)
        self.assertIn(str(error), response.json()['comment'])


class TestOISubmitSubmission(TestCase, OISubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_simple_submission(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 30, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.save()

        dt = datetime(2012, 7, 10, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSuspected(
                response,
                submission_number,
                suspected_number,
                str(SUSPICION_REASONS['BEFORE_START']),
            )

        dt = datetime(2012, 7, 31, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertNotSuspected(response, submission_number, suspected_number)

        dt = datetime(2012, 8, 5, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertNotSuspected(response, submission_number, suspected_number)

        dt = datetime(2012, 8, 10, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertNotSuspected(response, submission_number, suspected_number)

        dt = datetime(2012, 8, 11, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSuspected(
                response,
                submission_number,
                suspected_number,
                str(SUSPICION_REASONS['AFTER_END']),
            )

        dt = datetime(2012, 8, 9, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(
                contest, pi.short_name, dt, dt + timedelta(seconds=25)
            )
            self._assertNotSuspected(response, submission_number, suspected_number)

        dt = datetime(2012, 8, 9, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(
                contest, pi.short_name, dt, dt + timedelta(seconds=31)
            )
            self._assertSuspected(
                response,
                submission_number,
                suspected_number,
                str(SUSPICION_REASONS['TIMES_DIFFER']),
            )

        dt = datetime(2012, 8, 9, tzinfo=timezone.utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(
                contest, pi.short_name, dt + timedelta(seconds=31)
            )
            self._assertSuspected(
                response,
                submission_number,
                suspected_number,
                str(SUSPICION_REASONS['TIMES_DIFFER']),
            )

    def test_huge_submission(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        submission_number = Submission.objects.all().count()
        response = self.submit_file(contest, pi.short_name, file_size=102405)
        self._assertNotSubmitted(response, submission_number)

    def test_size_limit_accuracy(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        submission_number = Submission.objects.all().count()
        response = self.submit_file(contest, pi.short_name, file_size=102400)
        self._assertSubmitted(response, submission_number)

    def test_submissions_limitation(self):
        dt = datetime(2012, 8, 9, tzinfo=timezone.utc)
        with fake_time(dt):
            contest = Contest.objects.get()
            pi = ProblemInstance.objects.get()
            pi.submissions_limit = 1
            pi.save()
            submission_number = Submission.objects.all().count()
            suspected_number = Submission.objects.filter(kind='SUSPECTED').count()
            response = self.submit_file(contest, pi.short_name, dt, dt)
            self._assertNotSuspected(response, submission_number, suspected_number)
            response = self.submit_file(contest, pi.short_name, dt, dt)
            self._assertSuspected(
                response,
                submission_number + 1,
                suspected_number,
                str(SUSPICION_REASONS['SLE']),
            )

    def _assertUnsupportedExtension(self, contest, pi, name, ext):
        submission_number = Submission.objects.all().count()
        response = self.submit_file(
            contest, pi.short_name, file_name='%s.%s' % (name, ext)
        )
        self._assertNotSubmitted(response, submission_number)

    def test_extension_checking(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        self._assertUnsupportedExtension(contest, pi, 'xxx', '')
        self._assertUnsupportedExtension(contest, pi, 'xxx', 'e')
        self._assertUnsupportedExtension(contest, pi, 'xxx', 'cppp')
        submission_number = Submission.objects.all().count()
        response = self.submit_file(contest, pi.short_name, file_name='a.r.cpp')
        self._assertSubmitted(response, submission_number)

    def test_submission_form(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        submission_number = Submission.objects.all().count()
        response = self.submit_file(contest, pi.short_name, magickey="wrong")
        self._assertFormError(
            response, submission_number, INCORRECT_FORM_COMMENTS['magickey']
        )
        response = self.submit_file(contest, pi.short_name, localtime="wrong")
        self._assertFormError(
            response, submission_number, INCORRECT_FORM_COMMENTS['localtime']
        )
        response = self.submit_file(contest, pi.short_name, siotime="wrong")
        self._assertFormError(
            response, submission_number, INCORRECT_FORM_COMMENTS['siotime']
        )
        response = self.submit_file(contest, "xx")
        self._assertFormError(
            response, submission_number, INCORRECT_FORM_COMMENTS['problem_shortname']
        )
