from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.base.permissions import enforce_condition
from oioioi.contests.admin import ProblemInstanceAdmin
from oioioi.contests.models import ProblemInstance, Submission
from oioioi.contests.utils import contest_exists, is_contest_basicadmin
from oioioi.evalmgr.models import QueuedJob
from oioioi.suspendjudge.models import SuspendedProblem
from oioioi.suspendjudge.utils import is_suspended, is_suspended_on_init


class SuspendJudgeProblemInstanceAdminMixin(object):
    """Sets up admin panel for suspendjudge app."""

    def __init__(self, *args, **kwargs):
        super(SuspendJudgeProblemInstanceAdminMixin, self).__init__(*args, **kwargs)
        self.list_display = self.list_display + (
            'suspended_on_init_display',
            'suspended_on_final_display',
        )

    def _resume(self, instance_id):
        get_object_or_404(SuspendedProblem, problem_instance=instance_id).delete()

    def _rejudge(self, instance_id):
        suspended = Submission.objects.filter(
            queuedjob__state="SUSPENDED", problem_instance=instance_id
        )
        for submission in suspended:
            QueuedJob.objects.filter(submission=submission).delete()
            submission.problem_instance.controller.judge(submission)

    def _clear_queue(self, instance_id):
        QueuedJob.objects.filter(
            submission__problem_instance=instance_id, state="SUSPENDED"
        ).delete()

    def _suspend(self, problem_instance_id, suspend_init_tests=True):
        problem_instance = get_object_or_404(ProblemInstance, pk=problem_instance_id)
        SuspendedProblem.objects.get_or_create(
            problem_instance=problem_instance, suspend_init_tests=suspend_init_tests
        )

    @method_decorator(enforce_condition(contest_exists & is_contest_basicadmin))
    @method_decorator(require_POST)
    def resume_and_rejudge_view(self, request, problem_instance_id):
        self._resume(problem_instance_id)
        self._rejudge(problem_instance_id)
        return redirect('oioioiadmin:contests_probleminstance_changelist')

    @method_decorator(enforce_condition(contest_exists & is_contest_basicadmin))
    @method_decorator(require_POST)
    def resume_and_clear_view(self, request, problem_instance_id):
        self._resume(problem_instance_id)
        self._clear_queue(problem_instance_id)
        return redirect('oioioiadmin:contests_probleminstance_changelist')

    @method_decorator(enforce_condition(contest_exists & is_contest_basicadmin))
    @method_decorator(require_POST)
    def suspend_all_view(self, request, problem_instance_id):
        self._suspend(problem_instance_id)
        return redirect('oioioiadmin:contests_probleminstance_changelist')

    @method_decorator(enforce_condition(contest_exists & is_contest_basicadmin))
    @method_decorator(require_POST)
    def suspend_all_but_init_view(self, request, problem_instance_id):
        self._suspend(problem_instance_id, False)
        return redirect('oioioiadmin:contests_probleminstance_changelist')

    def _view_href(self, instance, view_name):
        return reverse(
            'oioioiadmin:suspendjudge_' + view_name,
            kwargs={'problem_instance_id': instance.pk},
        )

    def inline_actions(self, instance):
        if is_suspended(instance):
            actions = [
                (
                    self._view_href(instance, 'resume_and_rejudge'),
                    _("Resume and rejudge"),
                    'POST',
                ),
                (
                    self._view_href(instance, 'resume_and_clear'),
                    _("Resume and clear queue"),
                    'POST',
                ),
            ]
        else:
            actions = [
                (
                    self._view_href(instance, 'suspend_all'),
                    _("Suspend all tests"),
                    'POST',
                ),
                (
                    self._view_href(instance, 'suspend_all_but_init'),
                    _("Suspend final tests"),
                    'POST',
                ),
            ]
        return (
            super(SuspendJudgeProblemInstanceAdminMixin, self).inline_actions(instance)
            + actions
        )

    def suspended_on_init_display(self, instance):
        return not is_suspended_on_init(instance)

    suspended_on_init_display.short_description = _("Judge initial")
    suspended_on_init_display.boolean = True

    def suspended_on_final_display(self, instance):
        return not is_suspended(instance)

    suspended_on_final_display.short_description = _("Judge final")
    suspended_on_final_display.boolean = True

    def get_urls(self):
        urls = super(SuspendJudgeProblemInstanceAdminMixin, self).get_urls()
        extra_urls = [
            path(
                '<int:problem_instance_id>/resume_and_rejudge/',
                self.resume_and_rejudge_view,
                name='suspendjudge_resume_and_rejudge',
            ),
            path(
                '<int:problem_instance_id>/resume_and_clear/',
                self.resume_and_clear_view,
                name='suspendjudge_resume_and_clear',
            ),
            path(
                '<int:problem_instance_id>/suspend_all/',
                self.suspend_all_view,
                name='suspendjudge_suspend_all',
            ),
            path(
                '<int:problem_instance_id>/suspend_all_but_init/',
                self.suspend_all_but_init_view,
                name='suspendjudge_suspend_all_but_init',
            ),
        ]
        return extra_urls + urls


ProblemInstanceAdmin.mix_in(SuspendJudgeProblemInstanceAdminMixin)
