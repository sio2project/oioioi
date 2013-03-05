from django.contrib.admin import AllValuesFieldListFilter, SimpleListFilter
from django.contrib.admin.util import unquote
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from oioioi.base import admin
from oioioi.base.utils import make_html_links, make_html_link
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        Submission, ContestAttachment, RoundTimeExtension
from oioioi.contests.forms import SimpleContestForm, ProblemInstanceForm
from oioioi.participants.models import Participant
from oioioi.participants.controllers import ParticipantsController
from functools import partial
import urllib

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
        href = reverse('oioioi.contests.views.contest_attachment_view',
                    kwargs={'contest_id': str(instance.contest),
                            'attachment_id': str(instance.id)})
        return make_html_link(href, instance.content.name)

class ContestAdmin(admin.ModelAdmin):
    inlines = [RoundInline, AttachmentInline]
    fields = ['name', 'id', 'controller_name', 'default_submissions_limit']
    readonly_fields = ['creation_date']
    prepopulated_fields = {'id': ('name',)}
    list_display = ['name', 'id', 'creation_date']
    list_display_links = ['id', 'name']
    ordering = ['-creation_date']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if not obj:
            return True
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

class BaseContestAdmin(admin.MixinsAdmin):
    default_model_admin = ContestAdmin

    def _mixins_for_instance(self, request, instance):
        if instance:
            controller = instance.controller
            return controller.mixins_for_admin() + \
                    controller.registration_controller().mixins_for_admin()

admin.site.register(Contest, BaseContestAdmin)

admin.contest_admin_menu_registry.register('contest_change',
        _("Settings"),
        lambda request: reverse('oioioiadmin:contests_contest_change',
            args=(request.contest.id,)), order=20)

class ProblemInstanceAdmin(admin.ModelAdmin):
    form = ProblemInstanceForm
    fields = ('contest', 'round', 'problem', 'short_name')
    list_display = ('name_link', 'short_name_link', 'round', 'actions_field')
    readonly_fields = ('contest', 'problem')

    def has_add_permission(self, request):
        return False
#        return request.user.has_perm('contests.contest_admin', request.contest)

    def has_change_permission(self, request, obj=None):
        return not obj or request.user.has_perm('contests.contest_admin',
                obj.contest)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def _problem_change_href(self, instance):
        came_from = reverse('oioioiadmin:contests_probleminstance_changelist')
        return reverse('oioioiadmin:problems_problem_change',
                args=(instance.problem_id,)) + '?' + \
                        urllib.urlencode({'came_from': came_from})

    def _problem_reupload_href(self, instance):
        came_from = reverse('oioioiadmin:contests_probleminstance_changelist')
        return reverse('oioioiadmin:problems_problem_reupload',
                args=(instance.problem_id,)) + '?' + \
                        urllib.urlencode({'came_from': came_from})

    def _problem_download_href(self, instance):
        came_from = reverse('oioioiadmin:contests_probleminstance_changelist')
        return reverse('oioioiadmin:problems_problem_download',
                args=(instance.problem_id,)) + '?' + \
                        urllib.urlencode({'came_from': came_from})

    def inline_actions(self, instance):
        move_href = reverse('oioioiadmin:contests_probleminstance_change', args=(instance.id,))
        edit_href = self._problem_change_href(instance)
        reupload_href = self._problem_reupload_href(instance)
        download_href = self._problem_download_href(instance)
        return [
            (move_href, _("Move/rename")),
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

    def queryset(self, request):
        qs = super(ProblemInstanceAdmin, self).queryset(request)
        qs = qs.filter(contest=request.contest)
        qs = qs.select_related('contest', 'round', 'problem')
        return qs

admin.site.register(ProblemInstance, ProblemInstanceAdmin)

admin.contest_admin_menu_registry.register('problems_change',
        _("Problems"), lambda request:
        reverse('oioioiadmin:contests_probleminstance_changelist'),
        order=30)

class ProblemFilter(AllValuesFieldListFilter):
    title = _("problem")

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_login', 'user_full_name', 'date',
            'problem_instance_display', 'status_display', 'score_display']
    list_display_links = ['id', 'date']
    list_filter = ['problem_instance__problem__name', 'status']
    date_hierarchy = 'date'
    actions = ['rejudge_action']
    search_fields = ['user__username', 'user__last_name']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return request.user.has_perm('contests.contest_admin', request.contest)

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

    def rejudge_action(self, request, queryset):
        # Otherwise the submissions are rejudged in their default display
        # order which is "newest first"
        queryset = queryset.order_by('id')

        controller = request.contest.controller
        counter = 0
        for submission in queryset:
            controller.judge(submission)
            counter += 1
        self.message_user(request, _("Queued %d submissions for rejudge.")
                % (counter,))
    rejudge_action.short_description = _("Rejudge selected submissions")

    def queryset(self, request):
        queryset = super(SubmissionAdmin, self).queryset(request)
        queryset = queryset.filter(problem_instance__contest=request.contest)
        queryset = queryset.select_related('user', 'problem_instance',
                    'problem_instance__problem', 'problem_instance__contest')
        queryset = queryset.order_by('-id')
        return queryset

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return redirect('submission', contest_id=request.contest.id,
            submission_id=unquote(object_id))

admin.site.register(Submission, SubmissionAdmin)

admin.contest_admin_menu_registry.register('submissions_admin',
        _("Submissions"), lambda request:
        reverse('oioioiadmin:contests_submission_changelist'),
        order=40)

class RoundListFilter(SimpleListFilter):
    title = _("round")
    parameter_name = 'round'

    def lookups(self, request, model_admin):
        qs = model_admin.queryset(request)
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
    list_filter = [RoundListFilter]
    search_fields = ['user__username', 'user__last_name']

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

    def queryset(self, request):
        qs = super(RoundTimeExtensionAdmin, self).queryset(request)
        return qs.filter(round__contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest)
        elif db_field.name == 'user':
            rcontroller = request.contest.controller.registration_controller()
            if isinstance(rcontroller, ParticipantsController):
                kwargs['queryset'] = User.objects \
                        .filter(id__in=Participant.objects
                            .filter(contest=request.contest)
                            .values_list('user', flat=True)) \
                        .order_by('username')
        return super(RoundTimeExtensionAdmin, self) \
                .formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(RoundTimeExtension, RoundTimeExtensionAdmin)
admin.contest_admin_menu_registry.register('roundtimeextension_admin',
        _("Round extensions"), lambda request:
        reverse('oioioiadmin:contests_roundtimeextension_changelist'),
        order=50)
