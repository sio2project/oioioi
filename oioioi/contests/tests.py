from django.test import TestCase
from django.test.utils import override_settings
from django.template import Template, RequestContext
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.utils.timezone import utc, LocalTimezone
from django.contrib.auth.models import User, AnonymousUser
from oioioi.base.tests import check_not_accessible, fake_time
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        UserResultForContest, Submission, ContestAttachment, RoundTimeExtension
from oioioi.contests.scores import IntegerScore
from oioioi.contests.controllers import ContestController, \
        RegistrationController
from oioioi.problems.models import Problem, ProblemStatement, ProblemAttachment
from oioioi.programs.controllers import ProgrammingContestController
from datetime import datetime

class TestModels(TestCase):
    def test_fields_autogeneration(self):
        contest = Contest()
        contest.save()
        self.assertEqual(contest.id, 'c1')
        round = Round(contest=contest)
        round.save()
        self.assertEqual(round.name, 'Round 1')
        round = Round(contest=contest)
        round.save()
        self.assertEqual(round.name, 'Round 2')
        problem = Problem()
        problem.save()
        pi = ProblemInstance(round=round, problem=problem)
        pi.save()
        self.assertEqual(pi.contest, contest)

class TestScores(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_integer_score(self):
        s1 = IntegerScore(1)
        s2 = IntegerScore(2)
        self.assertLess(s1, s2)
        self.assertGreater(s2, s1)
        self.assertEqual(s1, IntegerScore(1))
        self.assertEqual((s1 + s2).value, 3)
        self.assertEqual(unicode(s1), '1')
        self.assertEqual(IntegerScore._from_repr(s1._to_repr()), s1)

    def test_score_field(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')

        instance = UserResultForContest(user=user, contest=contest,
                score=IntegerScore(42))
        instance.save()
        del instance

        instance = UserResultForContest.objects.get()
        self.assertTrue(isinstance(instance.score, IntegerScore))
        self.assertEqual(instance.score.value, 42)

        instance.score = "int:12"
        self.assertEqual(instance.score.value, 12)

        with self.assertRaises(ValidationError):
            instance.score = "1"
        with self.assertRaises(ValidationError):
            instance.score = "foo:1"

        instance.score = None
        instance.save()
        del instance

        instance = UserResultForContest.objects.get()
        self.assertIsNone(instance.score)


def print_contest_id_view(request, contest_id=None):
    return HttpResponse(str(request.contest.id))

def render_contest_id_view(request):
    t = Template('{{ contest.id }}')
    print RequestContext(request)
    return HttpResponse(t.render(RequestContext(request)))

class TestCurrentContest(TestCase):
    urls = 'oioioi.contests.test_urls'
    fixtures = ['test_two_empty_contests']

    @override_settings(DEFAULT_CONTEST='c2')
    def test_current_contest_session(self):
        self.assertEqual(self.client.get('/c/c1/id').content, 'c1')
        self.assertEqual(self.client.get('/contest_id').content, 'c1')
        self.assertEqual(self.client.get('/c/c2/id').content, 'c2')
        self.assertEqual(self.client.get('/contest_id').content, 'c2')

    def test_current_contest_most_recent(self):
        self.assertEqual(self.client.get('/contest_id').content, 'c2')

    @override_settings(DEFAULT_CONTEST='c1')
    def test_current_contest_from_settings(self):
        self.assertEqual(self.client.get('/contest_id').content, 'c1')

    @override_settings(DEFAULT_CONTEST='c2', ONLY_DEFAULT_CONTEST=True)
    def test_only_default_contest(self):
        self.assertEqual(self.client.get('/c/c1/id').status_code, 404)

    def test_current_contest_processor(self):
        #self.assertEqual(self.client.get('/contest_id').content, 'c2')
        self.assertEqual(self.client.get('/render_contest_id').content, 'c2')

class TestContestController(TestCase):
    def test_order_rounds_by_focus(self):
        r1 = Round(start_date=datetime(2012, 1, 1,  8,  0),
                   end_date=  datetime(2012, 1, 1, 10,  0))
        r2 = Round(start_date=datetime(2012, 1, 1,  9, 59),
                   end_date=  datetime(2012, 1, 1, 11, 00))
        r3 = Round(start_date=datetime(2012, 1, 2,  8,  0),
                   end_date=  datetime(2012, 1, 2, 10,  0))
        rounds = [r1, r2, r3]
        controller = ContestController(None)

        class FakeRequest(object):
            def __init__(self, timestamp):
                self.timestamp = timestamp
                self.user = AnonymousUser()

        for date, expected_order in (
                (datetime(2011, 1, 1), [r1, r2, r3]),
                (datetime(2012, 1, 1, 7, 0), [r1, r2, r3]),
                (datetime(2012, 1, 1, 7, 55), [r1, r2, r3]),
                (datetime(2012, 1, 1, 9, 40), [r1, r2, r3]),
                (datetime(2012, 1, 1, 9, 45), [r2, r1, r3]),
                (datetime(2012, 1, 1, 9, 59, 29), [r2, r1, r3]),
                (datetime(2012, 1, 1, 9, 59, 31), [r1, r2, r3]),
                (datetime(2012, 1, 1, 10, 0, 1), [r2, r3, r1]),
                (datetime(2012, 1, 1, 11, 0, 1), [r2, r3, r1]),
                (datetime(2012, 1, 2, 2, 0, 1), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 7, 55), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 9, 0), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 11, 0), [r3, r2, r1])):
            self.assertEqual(controller.order_rounds_by_focus(
                FakeRequest(date), rounds), expected_order)

class PrivateRegistrationController(RegistrationController):
    def anonymous_can_enter_contest(self):
        return False
    def filter_participants(self, queryset):
        return queryset.none()

class PrivateContestController(ContestController):
    def registration_controller(self):
        return PrivateRegistrationController(self.contest)

class TestContestViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_contest_visibility(self):
        invisible_contest = Contest(id='invisible', name='Invisible Contest',
            controller_name='oioioi.contests.tests.PrivateContestController')
        invisible_contest.save()
        response = self.client.get(reverse('select_contest'))
        self.assertIn('contests/select_contest.html',
                [t.name for t in response.templates])
        self.assertEqual(len(response.context['contests']), 1)
        self.client.login(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)
        self.client.login(username='test_admin')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Invisible Contest', response.content)

    def test_submission_view(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get(pk=1)
        self.client.login(username='test_user')
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('submission', kwargs=kwargs))
        def count_templates(name):
            return len([t for t in response.templates if t.name == name])
        self.assertEqual(count_templates('programs/submission_header.html'), 1)
        self.assertEqual(count_templates('programs/report.html'), 2)
        for t in ['0', '1ocen', '1a', '1b', '2', '3']:
            self.assertIn('<td>%s</td>' % (t,), response.content)
        self.assertEqual(response.content.count('34/34'), 1)
        self.assertEqual(response.content.count('0/33'), 2)
        self.assertEqual(response.content.count('0/0'), 2)
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_OK">OK</td>'), 5)  # One in the header
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_RE">Runtime error</td>'), 1)
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_WA">Wrong answer</td>'), 1)
        self.assertIn('program exited with code 1', response.content)

    def test_submissions_permissions(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get(pk=1)
        check_not_accessible(self, 'submission', kwargs={
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id})

        contest.controller_name = \
                'oioioi.contests.tests.PrivateContestController'
        contest.save()
        problem_instance = ProblemInstance.objects.get()
        problem = problem_instance.problem
        self.client.login(username='test_user')
        check_not_accessible(self, 'problems_list',
                kwargs={'contest_id': contest.id})
        check_not_accessible(self, 'problem_statement',
                kwargs={'contest_id': contest.id,
                    'problem_instance': problem_instance.short_name})
        check_not_accessible(self, 'my_submissions',
                kwargs={'contest_id': contest.id})
        check_not_accessible(self, 'contest_files',
                kwargs={'contest_id': contest.id})

class TestManyRounds(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission', 'test_extra_rounds']

    def test_problems_visibility(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            self.client.login(username='test_admin')
            response = self.client.get(url)
            for problem_name in ['zad1', 'zad2', 'zad3', 'zad4']:
                self.assertIn(problem_name, response.content)
            self.assertIn('contests/problems_list.html',
                    [t.name for t in response.templates])
            self.assertEqual(len(response.context['problem_instances']), 4)
            self.assertTrue(response.context['show_rounds'])
            self.client.login(username='test_user')
            response = self.client.get(url)
            self.assertNotIn('zad2', response.content)
            self.assertEqual(len(response.context['problem_instances']), 3)

    def test_submissions_visibility(self):
        contest = Contest.objects.get()
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            for problem_name in ['zad1', 'zad2', 'zad3', 'zad4']:
                self.assertNotIn(problem_name, response.content)
            self.assertIn('contests/my_submissions.html',
                    [t.name for t in response.templates])
            self.assertEqual(response.content.count('<td>34</td>'), 0)
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('<td>34</td>'), 4)

class TestMultilingualStatements(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_extra_statements']

    def test_multilingual_statements(self):
        pi = ProblemInstance.objects.get()
        url = reverse('problem_statement', kwargs={
            'contest_id': pi.contest.id,
            'problem_instance': pi.short_name})
        response = self.client.get(url)
        self.assertEqual('en-txt', response.content)
        self.client.cookies['lang'] = 'en'
        response = self.client.get(url)
        self.assertEqual('en-txt', response.content)
        self.client.cookies['lang'] = 'pl'
        response = self.client.get(url)
        self.assertEqual('pl-pdf', response.content)
        ProblemStatement.objects.filter(language='pl').delete()
        response = self.client.get(url)
        self.assertIn('%PDF', response.content)
        ProblemStatement.objects.get(language__isnull=True).delete()
        response = self.client.get(url)
        self.assertEqual('en-txt', response.content)


def failing_handler(env):
    raise RuntimeError('EXPECTED FAILURE')

class BrokenContestController(ProgrammingContestController):
    def fill_evaluation_environ(self, environ, submission):
        super(BrokenContestController, self).fill_evaluation_environ(environ,
                submission)
        environ['recipe'] = [
                ('failing_handler', 'oioioi.contests.tests.failing_handler'),
            ]

class TestRejudgeAndFailure(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_rejudge_request(self):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': 1}
        rejudge_url = reverse('rejudge_submission', kwargs=kwargs)
        self.client.login(username='test_admin')
        response = self.client.get(rejudge_url)
        self.assertEqual(405, response.status_code)

    def test_rejudge_and_failure(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.contests.tests.BrokenContestController'
        contest.save()

        submission = Submission.objects.get(pk=1)
        self.client.login(username='test_admin')
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.post(reverse('rejudge_submission',
                kwargs=kwargs))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertIn('failure report', response.content)
        self.assertIn('EXPECTED FAILURE', response.content)

        self.client.login(username='test_user')
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotIn('failure report', response.content)
        self.assertNotIn('EXPECTED FAILURE', response.content)

class TestContestAdmin(TestCase):
    fixtures = ['test_users']

    def test_simple_contest_create_and_change(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'name': 'cname',
                'id': 'cid',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': 'oioioi.programs.controllers.ProgrammingContestController'
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('was added successfully', response.content)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'cid')
        self.assertEqual(contest.name, 'cname')
        self.assertEqual(contest.round_set.count(), 1)
        round = contest.round_set.get()
        self.assertEqual(round.start_date,
                datetime(2012, 2, 3, 4, 5, 6, tzinfo=LocalTimezone()))
        self.assertEqual(round.end_date,
                datetime(2012, 2, 4, 5, 6, 7, tzinfo=LocalTimezone()))
        self.assertEqual(round.results_date,
                datetime(2012, 2, 5, 6, 7, 8, tzinfo=LocalTimezone()))

        url = reverse('oioioiadmin:contests_contest_change', args=('cid',)) \
                + '?simple=true'
        response = self.client.get(url)
        self.assertIn('2012-02-05', response.content)
        self.assertIn('06:07:08', response.content)

        post_data = {
                'name': 'cname1',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-04',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'cid')
        self.assertEqual(contest.name, 'cname1')
        self.assertEqual(contest.round_set.count(), 1)
        round = contest.round_set.get()
        self.assertEqual(round.start_date,
                datetime(2013, 2, 3, 14, 5, 6, tzinfo=LocalTimezone()))
        self.assertEqual(round.end_date,
                datetime(2013, 2, 4, 15, 6, 7, tzinfo=LocalTimezone()))
        self.assertEqual(round.results_date,
                datetime(2013, 2, 5, 16, 7, 8, tzinfo=LocalTimezone()))

        url = reverse('oioioiadmin:contests_contest_change', args=('cid',)) \
                + '?simple=true'
        response = self.client.get(url)
        post_data = {
                'name': 'cname1',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-01',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Start date should be before end date.",
                response.content)

class TestAttachments(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_attachments(self):
        contest = Contest.objects.get()
        problem = Problem.objects.get()
        ca = ContestAttachment(contest=contest,
                description='contest-attachment',
                content=ContentFile('content-of-conatt', name='conatt.txt'))
        ca.save()
        pa = ProblemAttachment(problem=problem,
                description='problem-attachment',
                content=ContentFile('content-of-probatt', name='probatt.txt'))
        pa.save()

        self.client.login(username='test_user')
        response = self.client.get(reverse('contest_files',
            kwargs={'contest_id': contest.id}))
        self.assertEqual(response.status_code, 200)
        for part in ['contest-attachment', 'conatt.txt', 'problem-attachment',
                'probatt.txt']:
            self.assertIn(part, response.content)
        response = self.client.get(reverse('contest_attachment',
            kwargs={'contest_id': contest.id, 'attachment_id': ca.id}))
        self.assertEqual(response.content, 'content-of-conatt')
        response = self.client.get(reverse('problem_attachment',
            kwargs={'contest_id': contest.id, 'attachment_id': pa.id}))
        self.assertEqual(response.content, 'content-of-probatt')

class SubmitFileMixin(object):
    def submit_file(self, contest, problem_instance, file_size=1024,
            file_name='submission.cpp'):
        url = reverse('submit', kwargs={'contest_id': contest.id})
        file = ContentFile('a' * file_size, name=file_name)
        post_data = {
            'problem_instance_id': problem_instance.id,
            'file': file
        }
        return self.client.post(url, post_data)

    def _assertSubmitted(self, contest, response):
        self.assertEqual(302, response.status_code)
        submissions = reverse('my_submissions',
                              kwargs={'contest_id': contest.id})
        self.assertTrue(response["Location"].endswith(submissions))

    def _assertNotSubmitted(self, contest, response):
        self.assertEqual(302, response.status_code)
        submissions = reverse('my_submissions',
                              kwargs={'contest_id': contest.id})
        self.assertFalse(response["Location"].endswith(submissions))


class TestSubmission(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def setUp(self):
        self.client.login(username='test_user')

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=utc)
        round.save()

        with fake_time(datetime(2012, 7, 10, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

        with fake_time(datetime(2012, 7, 31, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 10, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 11, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

    def test_huge_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        response = self.submit_file(contest, problem_instance, file_size=102405)
        self.assertIn('File size limit exceeded.', response.content)

    def test_size_limit_accuracy(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        response = self.submit_file(contest, problem_instance, file_size=102400)
        self._assertSubmitted(contest, response)

    def test_submit_limitation(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()

        for i in range(10):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        response = self.submit_file(contest, problem_instance)
        self.assertEqual(200, response.status_code)
        self.assertIn('Submission limit for the problem', response.content)

    def _assertUnsupportedExtension(self, contest, problem_instance, name, ext):
        response = self.submit_file(contest, problem_instance,
                file_name='%s.%s' % (name, ext))
        self.assertIn('Unknown or not supported file extension.',
                        response.content)

    def test_extension_checking(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', '')
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', 'e')
        self._assertUnsupportedExtension(contest, problem_instance,
                'xxx', 'cppp')
        response = self.submit_file(contest, problem_instance,
                file_name='a.tar.cpp')
        self._assertSubmitted(contest, response)

    @override_settings(SUBMITTABLE_EXTENSIONS=['c'])
    def test_limiting_extensions(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        self._assertUnsupportedExtension(contest, problem_instance,
                'xxx', 'cpp')
        response = self.submit_file(contest, problem_instance, file_name='a.c')
        self._assertSubmitted(contest, response)

class TestRoundExtension(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_extra_rounds',
             'test_full_package']

    def test_round_extension(self):
        contest = Contest.objects.get()
        round1 = Round.objects.get(pk=1)
        round2 = Round.objects.get(pk=2)
        problem_instance1 = ProblemInstance.objects.get(pk=1)
        problem_instance2 = ProblemInstance.objects.get(pk=2)
        self.assertTrue(problem_instance1.round == round1)
        self.assertTrue(problem_instance2.round == round2)
        round1.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round1.end_date = datetime(2012, 8, 5, tzinfo=utc)
        round1.save()
        round2.start_date = datetime(2012, 8, 10, tzinfo=utc)
        round2.end_date = datetime(2012, 8, 12, tzinfo=utc)
        round2.save()

        user = User.objects.get(username='test_user')
        ext = RoundTimeExtension(user=user, round=round1, extra_time=10)
        ext.save()

        with fake_time(datetime(2012, 8, 5, 0, 5, tzinfo=utc)):
            self.client.login(username='test_user2')
            response = self.submit_file(contest, problem_instance1)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)
            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance1)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 5, 0, 11, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance1)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

        with fake_time(datetime(2012, 8, 12, 0, 5, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance2)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

    def test_round_extension_admin(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:contests_roundtimeextension_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'user': '1001',
                'round': '1',
                'extra_time': '31415926'
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('was added successfully', response.content)
        self.assertEqual(RoundTimeExtension.objects.count(), 1)
        rext = RoundTimeExtension.objects.get()
        self.assertEqual(rext.round, Round.objects.get(pk=1))
        self.assertEqual(rext.user, User.objects.get(pk=1001))
        self.assertEqual(rext.extra_time, 31415926)

        url = reverse('oioioiadmin:contests_roundtimeextension_change', \
                args=('1',))
        response = self.client.get(url)
        self.assertIn('31415926', response.content)
        post_data = {
                'user': '1001',
                'round': '1',
                'extra_time': '27182818'
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoundTimeExtension.objects.count(), 1)
        rext = RoundTimeExtension.objects.get()
        self.assertEqual(rext.extra_time, 27182818)
