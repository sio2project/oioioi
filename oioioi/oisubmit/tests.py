from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.utils.timezone import utc
from oioioi.base.tests import fake_time
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        Submission
from oioioi.test_settings import OISUBMIT_MAGICKEY
from oioioi.oisubmit.err_dict import SUSPICION_REASONS, INCORRECT_FORM_COMMENTS

from datetime import datetime, timedelta
import json
import time

class OISubmitFileMixin(object):
    def submit_file(self, contest, pi_short_name, localtime=None,
                    siotime=None, magickey="",
                    file_size=1024, file_name='submission.cpp'):
        url = reverse('oisubmit', kwargs={'contest_id': contest.id})
        file = ContentFile('a' * file_size, name=file_name)

        if localtime is None:
            localtime = datetime.now()

        if isinstance(localtime, datetime):
            localtime_str = localtime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            localtime_str = localtime

        if not magickey:
            magickey = str(OISUBMIT_MAGICKEY)

        if siotime is None:
            siotime_str = ""
        elif isinstance(siotime, datetime):
            siotime_str = siotime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            siotime_str = siotime

        post_data = {
            'localtime': localtime_str,
            'siotime': siotime_str,
            'magickey': magickey,
            'problem_shortname': pi_short_name,
            'pi_id': str(0),
            'file': file
        }
        return self.client.post(url, post_data)

    def _json(self, response):
        return json.loads(response.content)

    def _assertSubmitted(self, response, submission_number):
        self.assertEqual(200, response.status_code)
        self.assertEqual(submission_number+1,
                         Submission.objects.all().count())

    def _assertNotSubmitted(self, response, submission_number):
        self.assertEqual(200, response.status_code)
        self.assertEqual(submission_number,
                         Submission.objects.all().count())

    def _assertSuspected(self, response, submission_number, reason):
        self._assertSubmitted(response, submission_number)
        self.assertEqual(True, self._json(response)['error_occured'])
        self.assertIn(reason, self._json(response)['comment'])

    def _assertFormError(self, response, submission_number, error):
        self._assertNotSubmitted(response, submission_number)
        self.assertIn(unicode(error), self._json(response)['comment'])

class TestOISubmitSubmission(TestCase, OISubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def setUp(self):
        self.client.login(username='test_user')

    def test_simple_submission(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=utc)
        round.save()

        dt = datetime(2012, 7, 10, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSuspected(response, submission_number,
                                  unicode(SUSPICION_REASONS['BEFORE_START']))

        dt = datetime(2012, 7, 31, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSubmitted(response, submission_number)

        dt = datetime(2012, 8, 5, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSubmitted(response, submission_number)

        dt = datetime(2012, 8, 10, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSubmitted(response, submission_number)

        dt = datetime(2012, 8, 11, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt)
            self._assertSuspected(response, submission_number,
                                  unicode(SUSPICION_REASONS['AFTER_END']))

        dt = datetime(2012, 8, 10, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt,
                                        dt + timedelta(seconds=29))
            self._assertSubmitted(response, submission_number)

        dt = datetime(2012, 8, 10, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name, dt,
                                        dt + timedelta(seconds=31))
            self._assertSuspected(response, submission_number,
                                  unicode(SUSPICION_REASONS['TIMES_DIFFER']))
        dt = datetime(2012, 8, 10, tzinfo=utc)
        with fake_time(dt):
            submission_number = Submission.objects.all().count()
            response = self.submit_file(contest, pi.short_name,
                                        dt + timedelta(seconds=31))
            self._assertSuspected(response, submission_number,
                                  unicode(SUSPICION_REASONS['TIMES_DIFFER']))

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
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        pi.submissions_limit = 1
        pi.save()
        submission_number = Submission.objects.all().count()
        response = self.submit_file(contest, pi.short_name)
        self._assertSubmitted(response, submission_number)
        response = self.submit_file(contest, pi.short_name)
        self._assertSuspected(response, submission_number+1,
                              unicode(SUSPICION_REASONS['SLE']))

    def _assertUnsupportedExtension(self, contest, pi, name, ext):
        submission_number = Submission.objects.all().count()
        response = self.submit_file(contest, pi.short_name,
                                    file_name='%s.%s' % (name, ext))
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
        self._assertFormError(response, submission_number,
                              INCORRECT_FORM_COMMENTS['magickey'])
        response = self.submit_file(contest, pi.short_name, localtime="wrong")
        self._assertFormError(response, submission_number,
                              INCORRECT_FORM_COMMENTS['localtime'])
        response = self.submit_file(contest, pi.short_name, siotime="wrong")
        self._assertFormError(response, submission_number,
                              INCORRECT_FORM_COMMENTS['siotime'])
        response = self.submit_file(contest, "xx")
        self._assertFormError(response, submission_number,
                              INCORRECT_FORM_COMMENTS['problem_shortname'])

