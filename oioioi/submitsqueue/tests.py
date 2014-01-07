from django.test import TestCase
from django.core.urlresolvers import reverse
from celery.exceptions import Ignore

from oioioi.submitsqueue.models import QueuedSubmit
from oioioi.submitsqueue.handlers import mark_submission_in_progress
from oioioi.contests.models import Submission, Contest
from oioioi.programs.controllers import ProgrammingContestController


class TestViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_submission']

    def _get_admin_site(self):
        self.client.login(username='test_admin')
        show_response = self.client.get(reverse(
                'oioioiadmin:submitsqueue_queuedsubmit_changelist'))
        self.assertEqual(show_response.status_code, 200)
        return show_response

    def assertStateCountEqual(self, state_str, count, show_response=None):
        """Asserts that the number of the submits with given state
           (``state_str``) that appear on the admin site is ``count``.
        """
        if show_response is None:
            show_response = self._get_admin_site()
        self.assertEqual(
                show_response.content.count('>' + state_str + '</span>'),
                count)

    def assertNotPresent(self, state_strs):
        """Asserts that none of the ``state_strs`` is present on the admin
           page
        """
        show_response = self._get_admin_site()
        for str in state_strs:
            self.assertStateCountEqual(str, 0, show_response)

    def test_admin_view(self):
        """Test if a submit shows on the list properly."""
        submission = Submission.objects.get(pk=1)
        qs = QueuedSubmit(submission=submission, state='QUEUED',
                          celery_task_id='dummy')
        qs.save()
        self.assertStateCountEqual('Queued', 1)

        qs.state = 'PROGRESS'
        qs.save()

        self.assertStateCountEqual('In progress', 1)

        qs.state = 'CANCELLED'
        qs.save()

        self.assertNotPresent(['In progress', 'Queued'])


class AddHandlersController(ProgrammingContestController):
    pass


class TestEval(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_submission']

    def test_add_handlers(self):
        """Test if the proper handlers are added to the recipe."""
        contest = Contest.objects.get()
        controller = AddHandlersController(contest)
        env = {}
        env['recipe'] = [('dummy', 'dummy')]
        env['postpone_handlers'] = [('dummy', 'dummy')]
        controller.finalize_evaluation_environment(env)

        self.assertIn(('mark_submission_in_progress',
                'oioioi.submitsqueue.handlers.mark_submission_in_progress'),
                env['recipe'])
        self.assertIn(('update_celery_task_id',
                'oioioi.submitsqueue.handlers.update_celery_task_id'),
                env['postpone_handlers'])
        self.assertIn(('remove_submission_on_error',
                'oioioi.submitsqueue.handlers.remove_submission_on_error'),
                env['error_handlers'])

    def test_revoke(self):
        """Test if a submit revokes properly."""
        job_id = 'dummy'
        env = {}
        env['job_id'] = job_id
        env['submission_id'] = 1

        submission = Submission.objects.get(pk=1)
        qs = QueuedSubmit(submission=submission, state='CANCELLED',
                          celery_task_id=job_id)
        qs.save()

        with self.assertRaises(Ignore):
            mark_submission_in_progress(env)
