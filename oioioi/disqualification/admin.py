from django.contrib.auth.models import User
from django.db import models
from django.forms import Textarea
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import Submission
from oioioi.contests.utils import is_contest_admin
from oioioi.disqualification.models import Disqualification, DisqualificationsConfig


class DisqualificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'submission_link', 'user_full_name', 'guilty_text']
    list_display_links = ['id', 'title', 'guilty_text']
    list_filter = ['guilty']
    search_fields = ['title', 'user__username', 'user__last_name']
    raw_id_fields = ['submission']
    exclude = ['contest']

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        # It's hard in django to autofill the 'user' field, when only
        # 'submission' is selected. This is because django.forms.models.py
        # calls _post_clean() even if there were errors in clean()
        obj.contest = request.contest
        obj.save()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'submission':
            qs = Submission.objects.filter(user__isnull=False)
            if request.contest:
                qs = qs.filter(problem_instance__contest=request.contest)
            kwargs['queryset'] = qs
        if db_field.name == 'user':
            qs = User.objects.all()
            if request.contest:
                qs = request.contest.controller.registration_controller().filter_participants(
                    qs
                )
            kwargs['queryset'] = qs
        return super(DisqualificationAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def submission_link(self, instance):
        if instance.submission is None:
            return ''
        reverse_kwargs = {
            'contest_id': instance.submission.problem_instance.contest_id,
            'submission_id': instance.submission_id,
        }
        return make_html_link(
            reverse('submission', kwargs=reverse_kwargs),
            '%d (%s)'
            % (
                instance.submission_id,
                force_str(instance.submission.problem_instance),
            ),
        )

    submission_link.short_description = _("Submission")

    def user_full_name(self, instance):
        return instance.user.get_full_name()

    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

    def guilty_text(self, instance):
        return _("Yes") if instance.guilty else _("No")

    guilty_text.short_description = _("Guilty")
    guilty_text.admin_order_field = 'guilty'

    def get_custom_list_select_related(self):
        return super(DisqualificationAdmin, self).get_custom_list_select_related() + [
            'submission',
            'user',
            'submission__problem_instance',
        ]

    def get_queryset(self, request):
        return (
            super(DisqualificationAdmin, self)
            .get_queryset(request)
            .filter(contest=request.contest)
            .order_by('-id')
        )


contest_site.contest_register(Disqualification, DisqualificationAdmin)
contest_admin_menu_registry.register(
    'disqualification_admin',
    _("Custom disqualification"),
    lambda request: reverse('oioioiadmin:disqualification_disqualification_changelist'),
    is_contest_admin,
    order=100,
)


class DisqualificationsConfigInline(admin.TabularInline):
    model = DisqualificationsConfig
    category = _("Advanced")
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 2})},
    }

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)


class DisqualificationsAdminMixin(object):
    """Adds :class:`~oioioi.disqualification.models.DisqualificationsConfigInline`
    to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(DisqualificationsAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (DisqualificationsConfigInline,)


ContestAdmin.mix_in(DisqualificationsAdminMixin)
