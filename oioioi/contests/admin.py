import threading
from functools import partial
from django.conf import settings

import urllib.parse

from django.contrib.admin import AllValuesFieldListFilter, SimpleListFilter
from django.contrib.admin.sites import NotRegistered
from django.contrib.admin.utils import quote, unquote
from django.db.models import Case, F, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.forms import ModelForm
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import re_path, reverse
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from oioioi.base import admin
from oioioi.base.admin import NO_CATEGORY, delete_selected
from oioioi.base.permissions import is_superuser
from oioioi.base.utils import make_html_link, make_html_links
from oioioi.base.utils.filters import ProblemNameListFilter
from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.contests.current_contest import set_cc_id
from oioioi.contests.forms import (
    ProblemInstanceForm,
    SimpleContestForm,
    TestsSelectionForm,
)
from oioioi.contests.menu import (
    contest_admin_menu_registry,
    contest_observer_menu_registry,
)
from oioioi.contests.models import (
    Contest,
    ContestAttachment,
    ContestLink,
    ContestPermission,
    ProblemInstance,
    Round,
    RoundTimeExtension,
    Submission,
    SubmissionReport,
    contest_permissions,
    submission_kinds,
)
from oioioi.contests.utils import (
    can_admin_contest,
    get_inline_for_contest,
    is_contest_owner,
    is_contest_admin,
    is_contest_archived,
    is_contest_basicadmin,
    is_contest_observer,
    create_contest_attributes
)
from oioioi.problems.models import ProblemName, ProblemPackage, ProblemSite
from oioioi.problems.utils import can_admin_problem
from oioioi.programs.models import Test, TestReport


class ContestProxyAdminSite(admin.AdminSite):
    def __init__(self, orig):
        super(ContestProxyAdminSite, self).__init__(orig.name)
        self._orig = orig

    def register(self, model_or_iterable, admin_class=None, **options):
        self._orig.register(model_or_iterable, admin_class, **options)

    def unregister(self, model_or_iterable):
        self._orig.unregister(model_or_iterable)
        try:
            super(ContestProxyAdminSite, self).unregister(model_or_iterable)
        except NotRegistered:
            pass

    def contest_register(self, model_or_iterable, admin_class=None, **options):
        super(ContestProxyAdminSite, self).register(
            model_or_iterable, admin_class, **options
        )

    def contest_unregister(self, model_or_iterable):
        super(ContestProxyAdminSite, self).unregister(model_or_iterable)

    def get_urls(self):
        self._registry.update(self._orig._registry)
        return super(ContestProxyAdminSite, self).get_urls()

    def index(self, request, extra_context=None):
        if request.contest:
            return super(ContestProxyAdminSite, self).index(request, extra_context)
        return self._orig.index(request, extra_context)

    def app_index(self, request, app_label, extra_context=None):
        if request.contest:
            return super(ContestProxyAdminSite, self).app_index(
                request, app_label, extra_context
            )
        return self._orig.app_index(request, app_label, extra_context)


#: Every contest-dependent model admin should be registered in this site
#: using the ``contest_register`` method. You can also register non-dependent
#: model admins like you would normally do using the ``register`` method.
#: Model admins registered using the ``contest_register`` method "don't exist"
#: when there is no active contest, that is, they can only be accessed
#: by a contest-prefixed URL and they don't show up in ``/admin/`` (but they
#: do in ``/c/<contest_id>/admin/``).
contest_site = ContestProxyAdminSite(admin.site)


class RoundInline(admin.StackedInline):
    model = Round
    extra = 0
    inline_classes = ('collapse open',)
    category = NO_CATEGORY

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def get_fieldsets(self, request, obj=None):
        fields = [
            'name',
            'start_date',
            'end_date',
            'results_date',
            'public_results_date',
            'is_trial',
        ]
        fields_no_public_results = [
            'name',
            'start_date',
            'end_date',
            'results_date',
            'is_trial',
        ]

        if (
            request.contest is not None
            and request.contest.controller.separate_public_results()
        ):
            fdsets = [(None, {'fields': fields})]
        else:
            fdsets = [(None, {'fields': fields_no_public_results})]
        return fdsets


class AttachmentInline(admin.StackedInline):
    model = ContestAttachment
    extra = 0
    readonly_fields = ['content_link']
    category = NO_CATEGORY

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def content_link(self, instance):
        if instance.id is not None:
            href = reverse(
                'contest_attachment',
                kwargs={
                    'contest_id': str(instance.contest.id),
                    'attachment_id': str(instance.id),
                },
            )
            return make_html_link(href, instance.content.name)
        return None

    content_link.short_description = _("Content file")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest)
        return super(AttachmentInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class ContestLinkInline(admin.TabularInline):
    model = ContestLink
    extra = 0
    category = _("Advanced")


class ContestAdmin(admin.ModelAdmin):
    inlines = [RoundInline, AttachmentInline, ContestLinkInline]
    readonly_fields = ['creation_date', 'school_year']
    prepopulated_fields = {'id': ('name',)}
    list_display = ['name', 'id', 'creation_date']
    list_display_links = ['id', 'name']
    ordering = ['-creation_date']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if not obj:
            return request.user.is_superuser
        return can_admin_contest(request.user, obj)

    def get_fields(self, request, obj=None):
        fields = [
            'name',
            'id',
            'school_year',
            'controller_name',
            'default_submissions_limit',
            'contact_email'
        ]
        if settings.USE_ACE_EDITOR:
            fields.append('enable_editor')

        if request.user.is_superuser:
            fields += ['judging_priority', 'judging_weight']

        fields += ['show_contest_rules']
        return fields

    def get_fieldsets(self, request, obj=None):
        if obj and not request.GET.get('simple', False):
            return super(ContestAdmin, self).get_fieldsets(request, obj)
        fields = list(SimpleContestForm().base_fields.keys())
        return [(None, {'fields': fields})]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            if obj.is_archived:
                return list(self.readonly_fields) + \
                    [field.name for field in obj._meta.fields] + \
                    [field.name for field in obj._meta.many_to_many]
            return self.readonly_fields + ['id', 'controller_name']
        return []

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return self.prepopulated_fields

    def get_inlines(self, request, obj):
        inlines = []
        for inline in self.inlines:
            inlines.append(get_inline_for_contest(inline, obj))
        return inlines

    def get_form(self, request, obj=None, **kwargs):
        if not self.has_change_permission(request, obj):
            return super(ContestAdmin, self).get_form(request, obj, **kwargs)

        if obj and not request.GET.get('simple', False):
            return super(ContestAdmin, self).get_form(request, obj, **kwargs)
        return modelform_factory(
            self.model,
            form=SimpleContestForm,
            formfield_callback=partial(self.formfield_for_dbfield, request=request),
            exclude=self.get_readonly_fields(request, obj),
        )

    def get_formsets(self, request, obj=None):
        if obj and not request.GET.get('simple', False):
            return super(ContestAdmin, self).get_formsets(request, obj)
        return []

    def response_change(self, request, obj):
        # Never redirect to the list of contests. Just re-display the edit
        # view.
        if '_popup' not in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return super(ContestAdmin, self).response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        default_redirection = super(ContestAdmin, self).response_add(
            request, obj, post_url_continue
        )
        if '_continue' in request.POST or '_addanother' in request.POST:
            return default_redirection
        else:
            return redirect('default_contest_view', contest_id=obj.id)

    def response_delete(self, request):
        set_cc_id(None)
        return super(ContestAdmin, self).response_delete(request)

    def _get_extra_context(self, extra_context):
        extra_context = extra_context or {}
        extra_context['categories'] = sorted(
            set([getattr(inline, 'category', None) for inline in self.inlines])
        )
        extra_context['no_category'] = NO_CATEGORY
        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = self._get_extra_context(extra_context)
        ret = super(ContestAdmin, self).add_view(request, form_url, extra_context)
        create_contest_attributes(request, True)
        return ret

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = self._get_extra_context(extra_context)
        # The contest's edit view uses request.contest, so editing a contest
        # when a different contest is active would produce weird results.
        contest_id = unquote(object_id)
        create_contest_attributes(request, False)
        if not request.contest or request.contest.id != contest_id:
            return redirect(
                'oioioiadmin:contests_contest_change', object_id, contest_id=contest_id
            )
        return super(ContestAdmin, self).change_view(
            request, object_id, form_url, extra_context
        )

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if not add:
            context.update({'show_unarchive': obj.is_archived})
            context.update({'show_archive': not obj.is_archived})
        return super().render_change_form(request, context, add, change, form_url, obj)

    def delete_selected_contests(self, modeladmin, request, queryset):
        # Redirect to contest-unprefixed view, just in case we deleted the current contest.
        return delete_selected(
            modeladmin,
            request,
            queryset,
            specific_redirect='noncontest:oioioiadmin:contests_contest_changelist',
        )

    def get_actions(self, request):
        # Use delete_selected with a custom redirect.
        actions = super(ContestAdmin, self).get_actions(request)
        actions['delete_selected'] = (
            self.delete_selected_contests,
            'delete_selected',
            delete_selected.short_description,
        )
        return actions


class BaseContestAdmin(admin.MixinsAdmin):
    default_model_admin = ContestAdmin

    def _mixins_for_instance(self, request, instance=None):
        if instance:
            controller = instance.controller
            return (
                controller.mixins_for_admin()
                + controller.registration_controller().mixins_for_admin()
            )


contest_site.register(Contest, BaseContestAdmin)

contest_admin_menu_registry.register(
    'contest_change',
    _("Settings"),
    lambda request: reverse(
        'oioioiadmin:contests_contest_change', args=(quote(request.contest.id),)
    ),
    order=20,
)


class ProblemInstanceAdmin(admin.ModelAdmin):
    form = ProblemInstanceForm
    fields = ('contest', 'round', 'problem', 'short_name', 'submissions_limit')
    list_display = ('name_link', 'short_name_link', 'round', 'package', 'actions_field')
    readonly_fields = ('contest', 'problem')
    ordering = ('-round__start_date', 'short_name')
    actions = ['attach_problems_to_another_contest']

    def attach_problems_to_another_contest(self, request, queryset):
        ids = [problem.id for problem in queryset]

        # Attach problem ids as arguments to the URL
        base_url = reverse('reattach_problem_contest_list')
        query_string = urlencode({'ids': ','.join(str(i) for i in ids)}, doseq=True)

        return redirect('%s?%s' % (base_url, query_string))

    def __init__(self, *args, **kwargs):
        # creating a thread local variable to store the request
        self._request_local = threading.local()
        self._request_local.request = None
        super(ProblemInstanceAdmin, self).__init__(*args, **kwargs)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if is_contest_archived(request):
            return False
        return is_contest_basicadmin(request)

    def has_delete_permission(self, request, obj=None):
        if is_contest_archived(request):
            return False
        return self.has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if is_contest_archived(request):
            return is_contest_basicadmin(request)
        return super(ProblemInstanceAdmin, self).has_view_permission(request, obj)

    def _problem_change_href(self, instance):
        came_from = reverse('oioioiadmin:contests_probleminstance_changelist')
        came_from_arg = urllib.parse.urlencode({'came_from': came_from})
        problem_change_base_href = reverse(
            'oioioiadmin:problems_problem_change', args=(instance.problem_id,)
        )
        return '%s?%s' % (problem_change_base_href, came_from_arg)

    def _rejudge_all_submissions_for_problem_href(self, instance):
        return reverse('rejudge_all_submissions_for_problem', args=(instance.id,))

    def _set_needs_rejudge_to_false_href(self, instance):
        return reverse('rejudge_not_needed', args=(instance.id,))

    def _model_solutions_href(self, instance):
        return reverse('model_solutions', args=(instance.id,))

    def _problem_site_href(self, instance):
        return reverse('problem_site', args=(instance.problem.problemsite.url_key,))

    def _reset_limits_href(self, instance):
        return reverse('reset_tests_limits_for_probleminstance', args=(instance.id,))

    def _reattach_problem_href(self, instance):
        base_url = reverse('reattach_problem_contest_list')
        query_string = urlencode({'ids': instance.id})
        # Attach problem id as an argument to the URL
        return '%s?%s' % (base_url, query_string)

    def _add_or_update_href(self, instance):
        return (
            reverse('problemset_add_or_update')
            + '?'
            + urllib.parse.urlencode(
                {'problem': instance.problem_id, 'key': 'upload'}
            )
        )

    def _replace_statement_href(self, instance):
        return (
            reverse('problem_site', args=(instance.problem.problemsite.url_key,))
            + '?'
            + urllib.parse.urlencode({'key': 'replace_problem_statement'})
        )

    def _package_manage_href(self, instance):
        return (
            reverse('problem_site', args=(instance.problem.problemsite.url_key,))
            + '?'
            + urllib.parse.urlencode({'key': 'manage_files_problem_package'})
        )

    def _edit_quiz_href(self, instance):
        return reverse('oioioiadmin:quizzes_quiz_change', args=[instance.problem.pk])

    def _move_href(self, instance):
        return reverse(
            'oioioiadmin:contests_probleminstance_change', args=(instance.id,)
        )

    def get_list_display(self, request):
        items = super(ProblemInstanceAdmin, self).get_list_display(request)
        if not is_contest_admin(request):
            disallowed_items = ['package']
            items = [item for item in items if item not in disallowed_items]
        return items

    def inline_actions(self, instance):
        result = []
        assert ProblemSite.objects.filter(problem=instance.problem).exists()
        move_href = self._move_href(instance)
        result.append((move_href, _("Edit")))
        is_quiz = hasattr(instance.problem, 'quiz') and instance.problem.quiz
        if is_quiz:
            edit_quiz_href = self._edit_quiz_href(instance)
            result.append((edit_quiz_href, _("Quiz questions")))
        else:
            models_href = self._model_solutions_href(instance)
            limits_href = self._reset_limits_href(instance)
            result.extend(
                [
                    (models_href, _("Model solutions")),
                    (limits_href, _("Reset tests limits")),
                ]
            )
        reattach_href = self._reattach_problem_href(instance)
        result.append((reattach_href, _("Attach to another contest")))
        problem_count = len(ProblemInstance.objects.filter(problem=instance.problem_id))
        # Problem package can only be reuploaded if the problem instance
        # is only in one contest and in the problem base
        # Package reupload does not apply to quizzes.
        if problem_count <= 2 and not is_quiz:
            add_or_update_href = self._add_or_update_href(instance)
            result.append((add_or_update_href, _("Reupload package")))
        if instance.needs_rejudge:
            rejudge_all_href = self._rejudge_all_submissions_for_problem_href(instance)
            result.append((rejudge_all_href, _("Rejudge all submissions for problem")))
            rejudge_not_needed_href = self._set_needs_rejudge_to_false_href(instance)
            result.append((rejudge_not_needed_href, _("Rejudge not needed")))

        problem_change_href = self._problem_change_href(instance)
        replace_statement_href = self._replace_statement_href(instance)
        package_manage_href = self._package_manage_href(instance)
        request = self._request_local.request
        if can_admin_problem(request, instance.problem):
            result.append((problem_change_href, _("Advanced settings")))
            result.append((replace_statement_href, _("Replace statement")))
            result.append((package_manage_href, _("Edit package")))
        return result

    def actions_field(self, instance):
        request = self._request_local.request
        if is_contest_archived(request):
            return _("Unarchive the contest to change this problem.")
        return make_html_links(self.inline_actions(instance))

    actions_field.short_description = _("Actions")

    def name_link(self, instance):
        href = self._problem_site_href(instance)
        return make_html_link(href, instance.problem.name)

    name_link.short_description = _("Problem")
    name_link.admin_order_field = 'ordering_name'

    def short_name_link(self, instance):
        href = self._problem_site_href(instance)
        return make_html_link(href, instance.short_name)

    short_name_link.short_description = _("Symbol")
    short_name_link.admin_order_field = 'short_name'

    def package(self, instance):
        problem_package = ProblemPackage.objects.filter(
            problem=instance.problem
        ).first()
        request = self._request_local.request
        if (
            problem_package
            and problem_package.package_file
            and can_admin_problem(request, instance.problem)
        ):
            href = reverse(
                'download_package', kwargs={'package_id': str(problem_package.id)}
            )
            return make_html_link(href, problem_package.package_file)
        return None

    package.short_description = _("Package file")

    def get_actions(self, request):
        self._request_local.request = request
        # Disable delete_selected.
        actions = super(ProblemInstanceAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_custom_list_select_related(self):
        return super(ProblemInstanceAdmin, self).get_custom_list_select_related() + [
            'contest',
            'round',
            'problem',
        ]

    def get_queryset(self, request):
        qs = super(ProblemInstanceAdmin, self).get_queryset(request)
        qs = (
            qs.filter(contest=request.contest)
            .annotate(
                localized_name=Subquery(
                    ProblemName.objects.filter(
                        problem=OuterRef('problem__pk'), language=get_language()
                    ).values('name')
                )
            )
            .annotate(
                ordering_name=Case(
                    When(localized_name__isnull=True, then=F('problem__legacy_name')),
                    default=F('localized_name'),
                )
            )
        )

        return qs

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_add_button'] = not is_contest_archived(request)
        return super(ProblemInstanceAdmin, self).changelist_view(
            request, extra_context=extra_context
        )


contest_site.contest_register(ProblemInstance, ProblemInstanceAdmin)


contest_admin_menu_registry.register(
    'problems_change',
    _("Problems"),
    lambda request: reverse('oioioiadmin:contests_probleminstance_changelist'),
    order=30,
)


class ProblemFilter(AllValuesFieldListFilter):
    title = _("problem")


class ContestsProblemNameListFilter(ProblemNameListFilter):
    initial_query_manager = Submission.objects
    contest_field = F('problem_instance__contest')
    related_names = 'problem_instance__problem__names'
    legacy_name_field = F('problem_instance__problem__legacy_name')
    outer_ref = OuterRef('problem_instance__problem__pk')


class SubmissionKindListFilter(SimpleListFilter):
    title = _("kind")
    parameter_name = 'kind'

    def lookups(self, request, model_admin):
        return submission_kinds

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(kind=self.value())
        else:
            return queryset


class SubmissionRoundListFilter(SimpleListFilter):
    title = _("round")
    parameter_name = 'round'

    def lookups(self, request, model_admin):
        r = []
        if request.contest:
            r = Round.objects.filter(contest=request.contest)
        return [(x, x) for x in r]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(problem_instance__round__name=self.value())
        else:
            return queryset


class ContestListFilter(SimpleListFilter):
    title = _("contest")
    parameter_name = 'contest'

    def lookups(self, request, model_admin):
        contests = list(Contest.objects.all())
        return [(x, x) for x in contests]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(problem_instance__contest__name=self.value())
        else:
            return queryset


class SystemErrorListFilter(SimpleListFilter):
    title = _("has active system error")
    parameter_name = 'has_active_system_error'

    def lookups(self, request, model_admin):
        return [('no', _("No")), ('yes', _("Yes"))]

    def queryset(self, request, queryset):
        q = Q(
            submissionreport__status='ACTIVE',
            submissionreport__failurereport__isnull=False,
        ) | Q(
            submissionreport__status='ACTIVE', submissionreport__testreport__status='SE'
        )
        if self.value() == 'yes':
            return queryset.filter(q)
        elif self.value() == 'no':
            return queryset.exclude(q)
        else:
            return queryset


class SubmissionAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    actions = ['rejudge_action']
    search_fields = [
        'user__username',
        'user__last_name',
        'problem_instance__problem__legacy_name',
        'problem_instance__short_name',
        'problem_instance__problem__names__name',
    ]

    class Media:
        js = ('admin/js/jquery.init.js', 'js/admin-filter-collapse.js')

    # We're using functions instead of lists because we want to
    # have different columns and filters depending on whether
    # contest is in url or not.
    def get_list_display(self, request):
        list_display = [
            'id',
            'user_login',
            'user_full_name',
            'date',
            'problem_instance_display',
            'contest_display',
            'status_display',
            'score_display',
        ]
        if request.contest:
            list_display.remove('contest_display')
        return list_display

    def get_list_display_links(self, request, list_display):
        return ['id', 'date']

    def get_list_filter(self, request):
        list_filter = [
            ContestsProblemNameListFilter,
            ContestListFilter,
            SubmissionKindListFilter,
            'status',
            SubmissionRoundListFilter,
            SystemErrorListFilter,
        ]
        if request.contest:
            list_filter.remove(ContestListFilter)
        else:
            list_filter.remove(SubmissionRoundListFilter)
        return list_filter

    def get_urls(self):
        urls = [re_path(r'^rejudge/$', self.rejudge_view)]
        return urls + super(SubmissionAdmin, self).get_urls()

    def rejudge_view(self, request):
        tests = request.POST.getlist('tests', [])
        subs_ids = [int(x) for x in request.POST.getlist('submissions', [])]
        rejudge_type = request.POST['rejudge_type']
        submissions = Submission.objects.in_bulk(subs_ids)
        all_reports_exist = True
        for sub in submissions.values():
            if not SubmissionReport.objects.filter(
                submission=sub, status='ACTIVE'
            ).exists():
                all_reports_exist = False
                break

        if all_reports_exist or rejudge_type == 'FULL':
            for sub in submissions.values():
                sub.problem_instance.controller.judge(
                    sub,
                    is_rejudge=True,
                    extra_args={'tests_to_judge': tests, 'rejudge_type': rejudge_type},
                )

            counter = len(submissions)
            self.message_user(
                request,
                ngettext_lazy(
                    "Queued one submission for rejudge.",
                    "Queued %(counter)d submissions for rejudge.",
                    counter,
                )
                % {'counter': counter},
            )
        else:
            self.message_user(
                request,
                _(
                    "Cannot rejudge submissions due to lack of active reports "
                    "for one or more submissions"
                ),
            )

        return redirect('oioioiadmin:contests_submission_changelist')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        # is_contest_observer() is required in here, because otherwise
        # observers get a 403 response. Any actions that modify submissions
        # will be blocked in get_actions()
        return is_contest_basicadmin(request) or is_contest_observer(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_basicadmin(request)

    def has_rejudge_permission(self, request):
        return is_contest_basicadmin(request)

    def get_actions(self, request):
        actions = super(SubmissionAdmin, self).get_actions(request)
        if not request.user.is_superuser:
            if not self.has_delete_permission(request):
                del actions['delete_selected']
            if not self.has_rejudge_permission(request):
                del actions['rejudge_action']
        return actions

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

    def problem_instance_display(self, instance):
        if instance.kind != 'NORMAL':
            return '%s (%s)' % (
                force_str(instance.problem_instance),
                force_str(instance.get_kind_display()),
            )
        else:
            return instance.problem_instance

    problem_instance_display.short_description = _("Problem")
    problem_instance_display.admin_order_field = 'problem_instance'

    def status_display(self, instance):
        return format_html(
            u'<span class="submission-admin submission submission--{}">{}</span>',
            instance.status,
            instance.get_status_display(),
        )

    status_display.short_description = _("Status")
    status_display.admin_order_field = 'status'

    def score_display(self, instance):
        return instance.get_score_display() or ''

    score_display.short_description = _("Score")
    score_display.admin_order_field = 'score_with_nulls_smallest'

    def contest_display(self, instance):
        return instance.problem_instance.contest

    contest_display.short_description = _("Contest")
    contest_display.admin_order_field = 'problem_instance__contest'

    def rejudge_action(self, request, queryset):
        # Otherwise the submissions are rejudged in their default display
        # order which is "newest first"
        queryset = queryset.order_by('id')

        pis = {s.problem_instance for s in queryset}
        pis_count = len(pis)
        sub_count = len(queryset)
        self.message_user(
            request,
            _(
                "You have selected %(sub_count)d submission(s) from "
                "%(pis_count)d problem(s)"
            )
            % {'sub_count': sub_count, 'pis_count': pis_count},
        )
        uses_is_active = False
        for pi in pis:
            if Test.objects.filter(problem_instance=pi, is_active=False).exists():
                uses_is_active = True
                break
        if not uses_is_active:
            for sub in queryset:
                if TestReport.objects.filter(
                    submission_report__submission=sub,
                    submission_report__status='ACTIVE',
                    test__is_active=False,
                ).exists():
                    uses_is_active = True
                    break

        return render(
            request,
            'contests/tests_choice.html',
            {'form': TestsSelectionForm(request, queryset, pis_count, uses_is_active)},
        )

    rejudge_action.short_description = _("Rejudge selected submissions")

    def get_custom_list_select_related(self):
        return super(SubmissionAdmin, self).get_custom_list_select_related() + [
            'user',
            'problem_instance',
            'problem_instance__problem',
            'problem_instance__contest',
        ]

    def get_queryset(self, request):
        queryset = super(SubmissionAdmin, self).get_queryset(request)
        if request.contest:
            queryset = queryset.filter(problem_instance__contest=request.contest)
        queryset = queryset.order_by('-id')

        # Because nulls are treated as highest by default,
        # this is a workaround to make them smaller than other values.
        queryset = queryset.annotate(
            score_with_nulls_smallest=Coalesce('score', Value(''))
        )
        return queryset

    def lookup_allowed(self, key, value):
        if key == 'user__username':
            return True
        return super(SubmissionAdmin, self).lookup_allowed(key, value)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        _contest_id = None
        if request.contest:
            _contest_id = request.contest.id
        if _contest_id is None:
            contest = Submission.objects.get(pk=object_id).problem_instance.contest
            if contest:
                _contest_id = contest.id
        return redirect(
            'submission', contest_id=_contest_id, submission_id=unquote(object_id)
        )


contest_site.register(Submission, SubmissionAdmin)

contest_admin_menu_registry.register(
    'submissions_admin',
    _("Submissions"),
    lambda request: reverse('oioioiadmin:contests_submission_changelist'),
    order=40,
)

contest_observer_menu_registry.register(
    'submissions_admin',
    _("Submissions"),
    lambda request: reverse('oioioiadmin:contests_submission_changelist'),
    order=40,
)

admin.system_admin_menu_registry.register(
    'managesubmissions_admin',
    _("All submissions"),
    lambda request: reverse(
        'oioioiadmin:contests_submission_changelist', kwargs={'contest_id': None}
    ),
    order=50,
)


class RoundTimeRoundListFilter(SimpleListFilter):
    title = _("round")
    parameter_name = 'round'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        return Round.objects.filter(id__in=qs.values_list('round')).values_list(
            'id', 'name'
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(round=self.value())
        else:
            return queryset


class RoundTimeExtensionAdmin(admin.ModelAdmin):
    list_display = ['user_login', 'user_full_name', 'round', 'extra_time']
    list_display_links = ['extra_time']
    list_filter = [RoundTimeRoundListFilter]
    search_fields = ['user__username', 'user__last_name']

    def has_add_permission(self, request):
        if is_contest_archived(request):
            return False
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        if is_contest_archived(request):
            return False
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        if is_contest_archived(request):
            return False
        return self.has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if is_contest_archived(request):
            return is_contest_admin(request)
        return super().has_view_permission(request, obj)

    def user_login(self, instance):
        if not instance.user:
            return ''
        return make_html_link(
            reverse(
                'user_info',
                kwargs={
                    'contest_id': instance.round.contest.id,
                    'user_id': instance.user.id,
                },
            ),
            instance.user.username,
        )

    user_login.short_description = _("Login")
    user_login.admin_order_field = 'user__username'

    def user_full_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.get_full_name()

    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

    def get_queryset(self, request):
        qs = super(RoundTimeExtensionAdmin, self).get_queryset(request)
        return qs.filter(round__contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest)
        return super(RoundTimeExtensionAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_custom_list_select_related(self):
        return super(RoundTimeExtensionAdmin, self).get_custom_list_select_related() + [
            'user',
            'round__contest',
        ]


contest_site.contest_register(RoundTimeExtension, RoundTimeExtensionAdmin)
contest_admin_menu_registry.register(
    'roundtimeextension_admin',
    _("Round extensions"),
    lambda request: reverse('oioioiadmin:contests_roundtimeextension_changelist'),
    is_contest_admin,
    order=50,
)


class ContestPermissionAdminForm(ModelForm):
    user = UserSelectionField(label=_("Username"))

    class Meta(object):
        model = ContestPermission
        fields = ('user', 'contest', 'permission')


class ContestPermissionAdmin(admin.ModelAdmin):
    list_display_links = ['user']
    ordering = ['permission', 'user']
    form = ContestPermissionAdminForm

    def user_full_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.get_full_name()

    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

    def get_list_display(self, request):
        fields = ['permission', 'user', 'user_full_name',]
        if not request.contest:
            fields.append('contest')
        return fields

    def has_add_permission(self, request):
        return is_contest_owner(request)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not request.contest:
            return False
        if obj is None:
            return is_contest_owner(request)
        # Contest owners can't manage other contests' permissions
        # and other contest owners.
        return (
            is_contest_owner(request) and
            request.contest == obj.contest and
            obj.permission != 'contests.contest_owner'
        )

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super(ContestPermissionAdmin, self).get_queryset(request)
        if request.contest:
            qs = qs.filter(contest=request.contest)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'contest':
            qs = Contest.objects
            if request.contest:
                qs = qs.filter(id=request.contest.id)
                kwargs['initial'] = request.contest
            kwargs['queryset'] = qs
        return super(ContestPermissionAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'permission':
            # Contest owners musn't manage other contest owners
            if not request.user.is_superuser:
                kwargs['choices'] = [
                    i for i in contest_permissions
                    if i[0] != 'contests.contest_owner'
                ]
        return super(ContestPermissionAdmin, self).formfield_for_choice_field(db_field, request, **kwargs)


contest_site.register(ContestPermission, ContestPermissionAdmin)
admin.system_admin_menu_registry.register(
    'contestspermission_admin',
    _("Contest rights"),
    lambda request: reverse('oioioiadmin:contests_contestpermission_changelist'),
    order=50,
)
contest_admin_menu_registry.register(
    'contestspermission_admin',
    _("Contest rights"),
    lambda request: reverse('oioioiadmin:contests_contestpermission_changelist'),
    is_contest_owner & ~is_superuser,
    order=50,
)
