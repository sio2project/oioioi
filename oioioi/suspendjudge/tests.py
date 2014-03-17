from celery.exceptions import Ignore
from django.test import TestCase
from django.core.urlresolvers import reverse

from oioioi.contests.models import ProblemInstance, Contest, Submission
from oioioi.suspendjudge.handlers import check_problem_instance_state
from oioioi.programs.controllers import ProgrammingContestController


class TestSuspendjudgeSuper(TestCase):
    def _empty_post(self, login, view, problem_instance):
        self.client.login(username=login)
        url = reverse('oioioiadmin:suspendjudge_' + view,
                      kwargs={'problem_instance_id': problem_instance.id})
        return self.client.post(url, {})


class TestViews(TestSuspendjudgeSuper):
    fixtures = ['test_users', 'test_permissions', 'test_contest']

    def test_views_permissions(self):
        problem_instance = ProblemInstance.objects.get()

        login_codes = {'test_user': 403, 'test_admin': 302,
                       'test_contest_admin': 302}
        views = ['suspend_all', 'resume_and_rejudge', 'suspend_all_but_init',
                 'resume_and_clear']

        for login in login_codes:
            for view in views:
                response = self._empty_post(login, view, problem_instance)
                self.assertEqual(response.status_code, login_codes[login])


class TestSuspending(TestSuspendjudgeSuper):
    fixtures = ['test_users', 'test_contest', 'test_submission',
                'test_full_package']

    def test_handler_presence(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get()
        controller = ProgrammingContestController(contest)

        env = {}
        env['recipe'] = [('dummy', 'dummy')]
        env['postpone_handlers'] = [('dummy', 'dummy')]
        env['extra_args'] = []
        controller.fill_evaluation_environ(env, submission)
        controller.finalize_evaluation_environment(env)

        self.assertIn(('check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state',
                dict(suspend_init_tests=True)), env['recipe'])
        self.assertIn(('check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state'),
                env['recipe'])

    def test_handler(self):
        problem_instance = ProblemInstance.objects.get()

        self._empty_post('test_admin', 'suspend_all', problem_instance)
        env = {'problem_instance_id': problem_instance.id, 'job_id': 'dummy',
               'submission_id': 1, 'is_rejudge': False,
               'report_kinds': ['INITIAL', 'NORMAL']}
        with self.assertRaises(Ignore):
            check_problem_instance_state(env, suspend_init_tests=True)

        self._empty_post('test_admin', 'resume_and_clear', problem_instance)
        self._empty_post('test_admin', 'suspend_all_but_init',
                         problem_instance)
        check_problem_instance_state(env, suspend_init_tests=True)
        with self.assertRaises(Ignore):
            check_problem_instance_state(env)
        env['is_rejudge'] = True
        env['report_kinds'] = ['HIDDEN']
        check_problem_instance_state(env)
