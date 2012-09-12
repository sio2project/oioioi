from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect
from django import forms
from django.forms.models import modelform_factory
from django.contrib.admin import widgets, AllValuesFieldListFilter
from django.contrib.admin.util import unquote
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from oioioi.base import admin
from oioioi.base.utils import make_html_links, make_html_link
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        Submission, ContestAttachment
from functools import partial
import datetime
import urllib

class SimpleContestForm(forms.ModelForm):
    class Meta:
        model = Contest
        fields = ['name', 'id', 'controller_name']

    start_date = forms.DateTimeField(widget=widgets.AdminSplitDateTime,
            label=_("Start date"))
    end_date = forms.DateTimeField(widget=widgets.AdminSplitDateTime,
            required=False, label=_("End date"))
    results_date = forms.DateTimeField(widget=widgets.AdminSplitDateTime,
            required=False, label=_("Results date"))

    def _generate_default_dates(self):
        now = datetime.datetime.now()
        self.initial['start_date'] = now
        self.initial['end_date'] = None
        self.initial['results_date'] = None

    def __init__(self, *args, **kwargs):
        super(SimpleContestForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            instance = kwargs['instance']
            rounds = instance.round_set.all()
            if len(rounds) > 1:
                raise ValueError("SimpleContestForm does not support contests "
                        "with more than one round.")
            if len(rounds) == 1:
                round = rounds[0]
                self.initial['start_date'] = round.start_date
                self.initial['end_date'] = round.end_date
                self.initial['results_date'] = round.results_date
            else:
                self._generate_default_dates()
        else:
            self._generate_default_dates()

    def save(self, commit=True):
        instance = super(SimpleContestForm, self).save(commit=False)
        rounds = instance.round_set.all()
        if len(rounds) > 1:
            raise ValueError("SimpleContestForm does not support contests "
                    "with more than one round.")
        if len(rounds) == 1:
            round = rounds[0]
        else:
            instance.save()
            round = Round(contest=instance, name=_("Round 1"))
        round.start_date = self.cleaned_data['start_date']
        round.end_date = self.cleaned_data['end_date']
        round.results_date = self.cleaned_data['results_date']
        round.save()

        if commit:
            instance.save()

        return instance

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
    extra = 1

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

class ContestAdmin(admin.ModelAdmin):
    inlines = [RoundInline, AttachmentInline]
    fields = ['name', 'id', 'controller_name']
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

class ProblemInstanceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(ProblemInstanceForm, self).__init__(*args, **kwargs)
        if instance:
            self.fields['round'].queryset = instance.contest.round_set

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
    list_display = ['id', 'user_login', 'user_full_name', 'date', 'problem_instance',
            'status_display', 'score_display']
    list_display_links = ['id', 'date']
    list_filter = ['user', 'problem_instance__problem__name', 'status']
    date_hierarchy = 'date'
    actions = ['rejudge_action']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return request.user.has_perm('contests.contest_admin', request.contest)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(self, request)

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
