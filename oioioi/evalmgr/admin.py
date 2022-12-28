import functools

from django.contrib.admin import SimpleListFilter
from django.db import transaction
from django.db.models import F, OuterRef
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from oioioi.base import admin
from oioioi.base.admin import system_admin_menu_registry
from oioioi.base.utils import make_html_link
from oioioi.base.utils.filters import ProblemNameListFilter
from oioioi.contests.admin import contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin
from oioioi.evalmgr.models import QueuedJob


class UserListFilter(SimpleListFilter):
    title = _("user")
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        users = list(
            set(
                QueuedJob.objects.filter(
                    submission__problem_instance__contest=request.contest
                ).values_list('submission__user__id', 'submission__user__username')
            )
        )

        if (None, None) in users:
            users = [x for x in users if x != (None, None)]
            users.append(('None', _("(None)")))
        return users

    def queryset(self, request, queryset):
        if self.value():
            if self.value() != 'None':
                return queryset.filter(submission__user=self.value())
            else:
                return queryset.filter(submission__user=None)
        else:
            return queryset


class EvalMgrProblemNameListFilter(ProblemNameListFilter):
    initial_query_manager = QueuedJob.objects
    contest_field = F('submission__problem_instance__contest')
    related_names = 'submission__problem_instance__problem__names'
    legacy_name_field = F('submission__problem_instance__problem__legacy_name')
    outer_ref = OuterRef('submission__problem_instance__problem__pk')


def _require_submission(function):
    @functools.wraps(function)
    def decorated(self, instance):
        if instance.submission is None:
            return None
        return function(self, instance)

    return decorated


def _require_problem_instance(function):
    @functools.wraps(function)
    def decorated(self, instance):
        if instance.submission.problem_instance is None:
            return None
        return function(self, instance)

    return _require_submission(decorated)


def _require_contest(function):
    @functools.wraps(function)
    def decorated(self, instance):
        if instance.submission.problem_instance.contest is None:
            return None
        return function(self, instance)

    return _require_problem_instance(decorated)


class SystemJobsQueueAdmin(admin.ModelAdmin):
    list_display = [
        'submit_id',
        'colored_state',
        'contest',
        'problem_instance',
        'user',
        'creation_date',
        'celery_task_id',
    ]
    list_filter = ['state', EvalMgrProblemNameListFilter]
    actions = ['remove_from_queue', 'delete_selected']

    def __init__(self, *args, **kwargs):
        super(SystemJobsQueueAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

    def _get_link(self, caption, app, *args, **kwargs):
        url = reverse(app, args=args, kwargs=kwargs)
        return make_html_link(url, caption)

    @_require_contest
    def _get_contest_id(self, instance):
        return instance.submission.problem_instance.contest_id

    def has_add_permission(self, request):
        return False

    def submit_id(self, instance):
        res = instance.submission_id
        return self._get_link(
            res,
            'submission',
            contest_id=self._get_contest_id(instance),
            submission_id=res,
        )

    submit_id.admin_order_field = 'submission__id'
    submit_id.short_description = _("Submission id")

    @_require_contest
    def problem_instance(self, instance):
        res = instance.submission.problem_instance
        return self._get_link(
            res,
            'problem_statement',
            contest_id=self._get_contest_id(instance),
            problem_instance=res.short_name,
        )

    problem_instance.admin_order_field = 'submission__problem_instance'
    problem_instance.short_description = _("Problem")

    @_require_contest
    def contest(self, instance):
        return self._get_link(
            instance.submission.problem_instance.contest,
            'default_contest_view',
            contest_id=self._get_contest_id(instance),
        )

    contest.admin_order_field = 'submission__problem_instance__contest'
    contest.short_description = _("Contest")

    @_require_submission
    def user(self, instance):
        return instance.submission.user

    user.admin_order_field = 'submission__user'
    user.short_description = _("User")

    def colored_state(self, instance):
        return format_html(
            u'<span class="submission-admin submission--{}">{}</span>',
            instance.state,
            instance.get_state_display(),
        )

    colored_state.short_description = _("Status")
    colored_state.admin_order_field = 'state'

    @transaction.atomic
    def remove_from_queue(self, request, queryset):
        for obj in queryset:
            obj.state = 'CANCELLED'
            obj.save()

    remove_from_queue.short_description = _(
        "Remove selected submissions from the queue"
    )

    def get_queryset(self, request):
        qs = super(SystemJobsQueueAdmin, self).get_queryset(request)
        return qs.exclude(state='CANCELLED')

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)

    def get_custom_list_select_related(self):
        return super(SystemJobsQueueAdmin, self).get_custom_list_select_related() + [
            'submission__problem_instance',
            'submission__problem_instance__contest',
            'submission__problem_instance__problem',
            'submission__user',
        ]


admin.site.register(QueuedJob, SystemJobsQueueAdmin)
system_admin_menu_registry.register(
    'queuedjob_admin',
    _("Evaluation queue"),
    lambda request: reverse('oioioiadmin:evalmgr_queuedjob_changelist'),
    order=60,
)


class ContestQueuedJob(QueuedJob):
    class Meta(object):
        proxy = True
        verbose_name = _("Contest Queued Jobs")


class ContestJobsQueueAdmin(SystemJobsQueueAdmin):
    def __init__(self, *args, **kwargs):
        super(ContestJobsQueueAdmin, self).__init__(*args, **kwargs)
        self.list_display = [
            x for x in self.list_display if x not in ('contest', 'celery_task_id_link')
        ]
        self.list_display_links = None
        self.list_filter = self.list_filter + [UserListFilter]

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return is_contest_admin(request)

    def get_queryset(self, request):
        qs = super(ContestJobsQueueAdmin, self).get_queryset(request)
        return qs.filter(submission__problem_instance__contest=request.contest)


contest_site.contest_register(ContestQueuedJob, ContestJobsQueueAdmin)
contest_admin_menu_registry.register(
    'queuedjob_admin',
    _("Evaluation queue"),
    lambda request: reverse('oioioiadmin:evalmgr_contestqueuedjob_changelist'),
    condition=(
        lambda request: not request.user.is_superuser and is_contest_admin(request)
    ),
    order=60,
)
