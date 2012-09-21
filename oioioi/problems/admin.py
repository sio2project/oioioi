from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.template.response import TemplateResponse
from django.template import RequestContext
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.util import unquote
from django.conf.urls import patterns, url
from django import forms
from oioioi.base import admin
from oioioi.base.utils import make_html_link, uploaded_file_name
from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.problems.models import Problem, ProblemStatement, \
        ProblemAttachment
from oioioi.problems.package import backend_for_package
from oioioi.problems.utils import can_add_problems, can_change_problem
import logging

logger = logging.getLogger(__name__)

class StatementInline(admin.TabularInline):
    model = ProblemStatement
    can_delete = False
    readonly_fields = ['language', 'content_link']
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request):
        return True

    def has_delete_permission(self, request):
        return False

    def content_link(self, instance):
        href = reverse('oioioi.problems.views.show_statement_view',
                kwargs={'statement_id': str(instance.id)})
        return make_html_link(href, instance.content.name)

class AttachmentInline(admin.TabularInline):
    model = ProblemAttachment
    can_delete = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request):
        return True

    def has_delete_permission(self, request):
        return False

class ProblemUploadForm(forms.Form):
    contest_id = forms.CharField(widget=forms.HiddenInput, required=False)
    package_file = forms.FileField(label=_("Package file"))

    def __init__(self, contest, *args, **kwargs):
        super(ProblemUploadForm, self).__init__(*args, **kwargs)

        if contest:
            choices = [(r.id, r.name) for r in contest.round_set.all()]
            if len(choices) == 1:
                self.fields.insert(0, 'round_id', forms.CharField(
                    widget=forms.HiddenInput, initial=choices[0][0]))
            else:
                self.fields.insert(0, 'round_id', forms.ChoiceField(
                    choices, label=_("Round")))

class ProblemAdmin(admin.ModelAdmin):
    inlines = [StatementInline, AttachmentInline]
    readonly_fields = ['name', 'short_name', 'controller_name',
            'package_backend_name']
    exclude = ['contest']
    list_filter = ['short_name']

    def has_add_permission(self, request):
        return can_add_problems(request)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return can_change_problem(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def redirect_to_list(self, request, problem):
        if problem.contest:
            return redirect('oioioiadmin:contests_probleminstance_changelist')
        else:
            return redirect('oioioiadmin:problems_problem_changelist')

    def add_view(self, request, form_url='', extra_context=None):
        return redirect('add_or_update_contest_problem',
                contest_id=request.contest.id)

    def download_view(self, request, object_id):
        problem = self.get_object(request, unquote(object_id))
        if not problem:
            raise Http404
        if not self.has_change_permission(request, problem):
            raise PermissionDenied
        try:
            return problem.package_backend.pack(problem)
        except NotImplementedError:
            self.message_user(request, _("Package not available for problem "
                "%s.") % (problem,))
            return self.redirect_to_list(request, problem)

    def queryset(self, request):
        queryset = super(ProblemAdmin, self).queryset(request)
        combined = queryset.none()
        if request.user.has_perm('problems.problems_db_admin'):
            combined |= queryset.filter(contest__isnull=True)
        if request.user.has_perm('contests.contest_admin', request.contest):
            combined |= queryset.filter(contest=request.contest)
        return combined

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        response = super(ProblemAdmin, self).delete_view(request, object_id,
                extra_context)
        if isinstance(response, HttpResponseRedirect):
            return self.redirect_to_list(request, obj)
        return response

class BaseProblemAdmin(admin.MixinsAdmin):
    default_model_admin = ProblemAdmin

    def _mixins_for_instance(self, request, instance):
        if instance:
            return instance.controller.mixins_for_admin()

    def reupload_view(self, request, object_id):
        model_admin = self._find_model_admin(request, object_id)
        return model_admin.reupload_view(request, object_id)

    def download_view(self, request, object_id):
        model_admin = self._find_model_admin(request, object_id)
        return model_admin.download_view(request, object_id)

    def get_urls(self):
        urls = super(BaseProblemAdmin, self).get_urls()
        extra_urls = patterns('',
            url(r'^(\d+)/download/$', self.download_view,
                name='problems_problem_download')
        )
        return extra_urls + urls

admin.site.register(Problem, BaseProblemAdmin)
