from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import (
    ContestAdmin,
    ContestsProblemNameListFilter,
    contest_site,
)
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin
from oioioi.mailsubmit.models import MailSubmission, MailSubmissionConfig
from oioioi.mailsubmit.utils import accept_mail_submission, is_mailsubmit_used


class MailSubmissionConfigInline(admin.TabularInline):
    model = MailSubmissionConfig
    category = _("Advanced")

    # We require superuser privileges, because it is unsafe to allow anyone
    # to edit printout_text. One can execute arbitrary shell command from
    # there.

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class MailSubmissionConfigAdminMixin(object):
    """Adds :class:`~oioioi.mailsubmit.models.MailSubmissionConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(MailSubmissionConfigAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (MailSubmissionConfigInline,)


ContestAdmin.mix_in(MailSubmissionConfigAdminMixin)


class MailSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user_login',
        'user_full_name',
        'date',
        'problem_instance',
        'related_submission',
        'accepted_by',
    ]
    list_display_links = None
    list_filter = [ContestsProblemNameListFilter]
    date_hierarchy = 'date'
    actions = ['accept_action']
    search_fields = ['user__username', 'user__last_name']

    def get_custom_list_select_related(self):
        return super(MailSubmissionAdmin, self).get_custom_list_select_related() + [
            'user',
            'accepted_by',
            'problem_instance__problem',
            'submission',
            'submission__problem_instance',
            'submission__problem_instance__contest',
        ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)

    def user_login(self, instance):
        if not instance.user:
            return ''
        return instance.user.username

    user_login.short_description = _("Login")
    user_login.admin_order_field = 'user__username'

    def user_full_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.get_full_name()

    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

    def related_submission(self, instance):
        if not instance.submission:
            return ''
        contest = instance.submission.problem_instance.contest
        href = reverse(
            'submission',
            kwargs={'contest_id': contest.id, 'submission_id': instance.submission_id},
        )
        return make_html_link(href, instance.submission_id)

    related_submission.short_description = _("Related submission")

    def accept_action(self, request, queryset):
        queryset = queryset.order_by('id')
        for mailsubmission in queryset:
            accept_mail_submission(request, mailsubmission)

    accept_action.short_description = _("Accept selected submissions")

    def get_queryset(self, request):
        queryset = super(MailSubmissionAdmin, self).get_queryset(request)
        queryset = queryset.filter(problem_instance__contest=request.contest)
        queryset = queryset.order_by('-id')
        return queryset

    def changelist_view(self, request, extra_context=None):
        return super(MailSubmissionAdmin, self).changelist_view(
            request, extra_context=extra_context
        )


contest_site.contest_register(MailSubmission, MailSubmissionAdmin)

contest_admin_menu_registry.register(
    'mail_submissions_admin',
    _("Postal submissions"),
    lambda request: reverse('oioioiadmin:mailsubmit_mailsubmission_changelist'),
    order=40,
    condition=is_mailsubmit_used,
)
