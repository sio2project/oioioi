from functools import partial
import urllib

from django.conf.urls import patterns
from django.contrib.admin import AllValuesFieldListFilter, SimpleListFilter
from django.contrib.admin.util import unquote, quote
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import redirect, render
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode

from oioioi.base import admin
from oioioi.base.utils import make_html_links, make_html_link
from oioioi.contests.forms import ProblemInstanceForm, SimpleContestForm, \
        TestsSelectionForm
from oioioi.contests.menu import contest_admin_menu_registry, \
        contest_observer_menu_registry
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        Submission, ContestAttachment, RoundTimeExtension, ContestPermission, \
        submission_kinds, ContestLink, SubmissionReport
from oioioi.contests.utils import is_contest_admin, is_contest_observer
from oioioi.programs.models import Test, TestReport


class RoundInline(admin.StackedInline):
    model = Round
    extra = 0
    inline_classes = ('collapse open',)

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def get_fieldsets(self, request, obj=None):
        fields = ['name', 'start_date', 'end_date', 'results_date',
                'public_results_date', 'is_trial']
        fields_no_public_results = ['name', 'start_date', 'end_date',
            'results_date', 'is_trial']

        if request.contest.controller.separate_public_results():
            fdsets = [(None, {'fields': fields})]
        else:
            fdsets = [(None, {'fields': fields_no_public_results})]
        return fdsets


class AttachmentInline(admin.TabularInline):
    model = ContestAttachment
    extra = 0
    readonly_fields = ['content_link']

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def content_link(self, instance):
        if instance.id is not None:
            href = reverse('oioioi.contests.views.contest_attachment_view',
                        kwargs={'contest_id': str(instance.contest.id),
                                'attachment_id': str(instance.id)})
            return make_html_link(href, instance.content.name)
        return None
    content_link.short_description = _("Content file")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest)
        return super(AttachmentInline, self) \
            .formfield_for_foreignkey(db_field, request, **kwargs)


class ContestLinkInline(admin.TabularInline):
    model = ContestLink
    extra = 0


class ContestAdmin(admin.ModelAdmin):
    inlines = [RoundInline, AttachmentInline, ContestLinkInline]
    fields = ['name', 'id', 'controller_name', 'default_submissions_limit',
              'contact_email']
    readonly_fields = ['creation_date']
    prepopulated_fields = {'id': ('name',)}
    list_display = ['name', 'id', 'creation_date']
    list_display_links = ['id', 'name']
    ordering = ['-creation_date']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if not obj:
            return request.user.is_superuser
        return request.user.has_perm('contests.contest_admin', obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_fieldsets(self, request, obj=None):
        if obj and not request.GET.get('simple', False):
            return super(ContestAdmin, self).get_fieldsets(request, obj)
        fields = SimpleContestForm().base_fields.keys()
        return [(None, {'fields': fields})]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['id', 'controller_name']
        return []

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return self.prepopulated_fields

    def get_form(self, request, obj=None, **kwargs):
        if obj and not request.GET.get('simple', False):
            return super(ContestAdmin, self).get_form(request, obj, **kwargs)
        return modelform_factory(self.model,
                form=SimpleContestForm,
                formfield_callback=partial(self.formfield_for_dbfield,
                    request=request),
                exclude=self.get_readonly_fields(request, obj))

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
        default_redirection = super(ContestAdmin, self).response_add(request,
                obj, post_url_continue)
        request.session['contest_id'] = obj.id
        if '_continue' in request.POST or '_addanother' in request.POST:
            return default_redirection
        else:
            return redirect('default_contest_view', contest_id=obj.id)


class BaseContestAdmin(admin.MixinsAdmin):
    default_model_admin = ContestAdmin

    def _mixins_for_instance(self, request, instance=None):
        if instance:
            controller = instance.controller
            return controller.mixins_for_admin() + \
                    controller.registration_controller().mixins_for_admin()

admin.site.register(Contest, BaseContestAdmin)

contest_admin_menu_registry.register('contest_change', _("Settings"),
        lambda request: reverse('oioioiadmin:contests_contest_change',
            args=(quote(request.contest.id),)), order=20)


class ProblemInstanceAdmin(admin.ModelAdmin):
    form = ProblemInstanceForm
    fields = ('contest', 'round', 'problem', 'short_name')
    list_display = ('name_link', 'short_name_link', 'round', 'actions_field')
    readonly_fields = ('contest', 'problem')
    ordering = ('-round__start_date', 'short_name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.contest is not None and is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def _problem_change_href(self, instance):
        came_from = reverse('oioioiadmin:contests_probleminstance_changelist')
        return reverse('oioioiadmin:problems_problem_change',
                args=(instance.problem_id,)) + '?' + \
                        urllib.urlencode({'came_from': came_from})

    def _problem_reupload_href(self, instance):
        return reverse('add_or_update_contest_problem',
                kwargs={'contest_id': instance.contest.id}) + '?' + \
                        urllib.urlencode({'problem': instance.problem.id})

    def _problem_download_href(self, instance):
        came_from = reverse('oioioiadmin:contests_probleminstance_changelist')
        return reverse('oioioiadmin:problems_problem_download',
                args=(instance.problem_id,)) + '?' + \
                        urllib.urlencode({'came_from': came_from})

    def probleminstance_change_link_name(self):
        return _("Edit problem instance")

    def inline_actions(self, instance):
        move_href = reverse('oioioiadmin:contests_probleminstance_change',
                args=(instance.id,))
        edit_href = self._problem_change_href(instance)
        reupload_href = self._problem_reupload_href(instance)
        download_href = self._problem_download_href(instance)
        return [
            (move_href, self.probleminstance_change_link_name()),
            (edit_href, _("Edit problem")),
            (reupload_href, _("Re-upload")),
            (download_href, _("Download package")),
        ]

    def actions_field(self, instance):
        return make_html_links(self.inline_actions(instance))
    actions_field.allow_tags = True
    actions_field.short_description = _("Actions")

    def name_link(self, instance):
        href = self._problem_change_href(instance)
        return make_html_link(href, instance.problem.name)
    name_link.allow_tags = True
    name_link.short_description = _("Problem")
    name_link.admin_order_field = 'problem__name'

    def short_name_link(self, instance):
        href = self._problem_change_href(instance)
        return make_html_link(href, instance.short_name)
    short_name_link.allow_tags = True
    short_name_link.short_description = _("Symbol")
    short_name_link.admin_order_field = 'short_name'

    def get_actions(self, request):
        # Disable delete_selected.
        actions = super(ProblemInstanceAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_list_select_related(self):
        return super(ProblemInstanceAdmin, self).get_list_select_related() \
                + ['contest', 'round', 'problem']

    def get_queryset(self, request):
        qs = super(ProblemInstanceAdmin, self).get_queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs

admin.site.register(ProblemInstance, ProblemInstanceAdmin)

contest_admin_menu_registry.register('problems_change',
        _("Problems"), lambda request:
        reverse('oioioiadmin:contests_probleminstance_changelist'),
        order=30)


class ProblemFilter(AllValuesFieldListFilter):
    title = _("problem")


class UserListFilter(SimpleListFilter):
    title = _("user")
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        # Unique users that have submitted something in this contest
        users = list(Submission.objects
                .filter(problem_instance__contest=request.contest)
                .distinct()
                .order_by('user__username')
                .values_list('user__id', 'user__username'))
        if (None, None) in users:
            users = [x for x in users if x != (None, None)]
            users.append(('None', _("(None)")))
        return users

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value() == 'None':
            return queryset.filter(user=None)
        if self.value().isdigit():
            return queryset.filter(user=self.value())

        raise Http404("Incorrect user filter")


class ProblemNameListFilter(SimpleListFilter):
    title = _("problem")
    parameter_name = 'pi'

    def lookups(self, request, model_admin):
        # Unique problem names
        p_names = list(set(ProblemInstance.objects
                .filter(contest=request.contest)
                .values_list('problem__name', flat=True)))
        return [(x, x) for x in p_names]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                    problem_instance__problem__name=self.value())
        else:
            return queryset


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
        r = Round.objects.filter(contest=request.contest)
        return [(x, x) for x in r]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(problem_instance__round__name=self.value())
        else:
            return queryset


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_login', 'user_full_name', 'date',
            'problem_instance_display', 'status_display', 'score_display']
    list_display_links = ['id', 'date']
    list_filter = [UserListFilter, ProblemNameListFilter,
            SubmissionKindListFilter, 'status', SubmissionRoundListFilter]
    date_hierarchy = 'date'
    actions = ['rejudge_action']
    search_fields = ['user__username', 'user__last_name']

    def get_urls(self):
        urls = patterns('',
                        (r'^rejudge/$', self.rejudge_view))
        return urls + super(SubmissionAdmin, self).get_urls()

    def rejudge_view(self, request):
        tests = request.POST.getlist('tests', [])
        subs_ids = [int(x) for x in request.POST.getlist('submissions', [])]
        rejudge_type = request.POST['rejudge_type']
        controller = request.contest.controller
        submissions = Submission.objects.in_bulk(subs_ids)
        all_reports_exist = True
        for sub in submissions.values():
            if not SubmissionReport.objects.filter(submission=sub,
                                                   status='ACTIVE') \
                                           .exists():
                all_reports_exist = False
                break

        if all_reports_exist or rejudge_type == 'FULL':
            for sub in submissions.values():
                controller.judge(sub,
                                 is_rejudge=True,
                                 extra_args={'tests_to_judge': tests,
                                             'rejudge_type': rejudge_type})

            counter = len(submissions)
            self.message_user(
                request,
                ungettext_lazy("Queued one submission for rejudge.",
                               "Queued %(counter)d submissions for rejudge.",
                               counter) % {'counter': counter})
        else:
            self.message_user(
                request,
                _("Cannot rejudge submissions due to lack of active reports "
                  "for one or more submissions"))

        return redirect('oioioiadmin:contests_submission_changelist')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return is_contest_admin(request) or is_contest_observer(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request)

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
            return '%s (%s)' % (force_unicode(instance.problem_instance),
                    force_unicode(instance.get_kind_display()))
        else:
            return instance.problem_instance
    problem_instance_display.short_description = _("Problem")
    problem_instance_display.admin_order_field = 'problem_instance'

    def status_display(self, instance):
        return '<span class="subm_admin subm_status subm_%s">%s</span>' % \
                (instance.status, conditional_escape(force_unicode(
                    instance.get_status_display())))
    status_display.allow_tags = True
    status_display.short_description = _("Status")
    status_display.admin_order_field = 'status'

    def score_display(self, instance):
        return instance.get_score_display() or ''
    score_display.short_description = _("Score")
    score_display.admin_order_field = 'score'


    def rejudge_action(self, request, queryset):
        # Otherwise the submissions are rejudged in their default display
        # order which is "newest first"
        queryset = queryset.order_by('id')

        pis = {s.problem_instance for s in queryset}
        pis_count = len(pis)
        sub_count = len(queryset)
        self.message_user(
            request,
            _("You have selected %(sub_count)d submission(s) from "
              "%(pis_count)d problem(s)") % {'sub_count': sub_count,
                                                'pis_count': pis_count})
        uses_is_active = False
        for pi in pis:
            if Test.objects.filter(problem_instance=pi,
                                   is_active=False) \
                           .exists():
                uses_is_active = True
                break
        if not uses_is_active:
            for sub in queryset:
                if TestReport.objects.filter(
                        submission_report__submission=sub,
                        submission_report__status='ACTIVE',
                        test__is_active=False).exists():
                    uses_is_active = True
                    break

        return render(request, 'contests/tests_choice.html',
                      {'form': TestsSelectionForm(request,
                                                  queryset,
                                                  pis_count,
                                                  uses_is_active)})
    rejudge_action.short_description = _("Rejudge selected submissions")

    def get_list_select_related(self):
        return super(SubmissionAdmin, self).get_list_select_related() \
                + ['user', 'problem_instance', 'problem_instance__problem',
                   'problem_instance__contest']

    def get_queryset(self, request):
        queryset = super(SubmissionAdmin, self).get_queryset(request)
        queryset = queryset.filter(problem_instance__contest=request.contest)
        queryset = queryset.order_by('-id')
        return queryset

    def lookup_allowed(self, key, value):
        if key == 'user__username':
            return True
        return super(SubmissionAdmin, self).lookup_allowed(key, value)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return redirect('submission', contest_id=request.contest.id,
            submission_id=unquote(object_id))

admin.site.register(Submission, SubmissionAdmin)

contest_admin_menu_registry.register('submissions_admin', _("Submissions"),
        lambda request: reverse('oioioiadmin:contests_submission_changelist'),
        order=40)

contest_observer_menu_registry.register('submissions_admin', _("Submissions"),
        lambda request: reverse('oioioiadmin:contests_submission_changelist'),
        order=40)


class RoundTimeRoundListFilter(SimpleListFilter):
    title = _("round")
    parameter_name = 'round'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        return Round.objects.filter(id__in=qs.values_list('round')) \
                .values_list('id', 'name')

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
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def user_login(self, instance):
        if not instance.user:
            return ''
        return make_html_link(
                reverse('user_info', kwargs={
                        'contest_id': instance.round.contest.id,
                        'user_id': instance.user.id}),
                instance.user.username)
    user_login.short_description = _("Login")
    user_login.admin_order_field = 'user__username'
    user_login.allow_tags = True

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
        return super(RoundTimeExtensionAdmin, self) \
                .formfield_for_foreignkey(db_field, request, **kwargs)

    def get_list_select_related(self):
        return super(RoundTimeExtensionAdmin, self).get_list_select_related() \
                + ['user', 'round__contest']

admin.site.register(RoundTimeExtension, RoundTimeExtensionAdmin)
contest_admin_menu_registry.register('roundtimeextension_admin',
        _("Round extensions"), lambda request:
        reverse('oioioiadmin:contests_roundtimeextension_changelist'),
        order=50)


class ContestPermissionAdmin(admin.ModelAdmin):
    list_display = ['permission', 'user', 'user_full_name']
    list_display_links = ['user']
    ordering = ['permission', 'user']

    def user_full_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.get_full_name()
    user_full_name.short_description = _("User name")
    user_full_name.admin_order_field = 'user__last_name'

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
        return super(ContestPermissionAdmin, self) \
                .formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(ContestPermission, ContestPermissionAdmin)
admin.system_admin_menu_registry.register('contestspermission_admin',
        _("Contest rights"), lambda request:
        reverse('oioioiadmin:contests_contestpermission_changelist'),
        order=50)
