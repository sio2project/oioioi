from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.util import unquote
from django.conf.urls import patterns, url
from oioioi.base import admin
from oioioi.base.utils import make_html_link, uploaded_file_name
from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.problems.forms import ProblemUploadForm
from oioioi.problems.models import Problem, ProblemStatement, \
        ProblemAttachment
from oioioi.problems.package import backend_for_package
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
    extra = 0
    readonly_fields = ['content_link']

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def content_link(self, instance):
        href = reverse('oioioi.problems.views.show_problem_attachment_view',
                kwargs={'attachment_id': str(instance.id)})
        return make_html_link(href, instance.content.name)

class ProblemInstanceInline(admin.StackedInline):
    model = ProblemInstance
    can_delete = False
    fields = ['submissions_limit']
    inline_classes = ('collapse open',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request):
        return True

    def has_delete_permission(self, request):
        return False

class ProblemAdmin(admin.ModelAdmin):
    inlines = [StatementInline, AttachmentInline, ProblemInstanceInline]
    readonly_fields = ['name', 'short_name', 'controller_name',
            'package_backend_name']
    exclude = ['contest']
    list_filter = ['short_name']

    def has_add_permission(self, request):
        return request.user.has_perm('problems.problems_db_admin') \
                or request.user.has_perm('contests.contest_admin',
                        request.contest)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        if request.user.has_perm('problems.problems_db_admin'):
            return True
        if request.user.has_perm('problems.problem_admin', obj):
            return True
        if obj.contest and request.user.has_perm('contests.contest_admin',
                obj.contest):
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def redirect_to_list(self, request, problem):
        if problem.contest:
            return redirect('oioioiadmin:contests_probleminstance_changelist')
        else:
            return redirect('oioioiadmin:problems_problem_changelist')

    def _add_problem(self, request, round, submissions_limit):
        uploaded_file = request.FILES['package_file']
        with uploaded_file_name(uploaded_file) as filename:
            backend = backend_for_package(filename,
                    original_filename=uploaded_file.name)
            problem = backend.unpack(filename,
                    original_filename=uploaded_file.name)
            if not problem.package_backend_name:
                raise AssertionError("Problem package backend (%r) did not "
                        "set Problem.package_backend_name. This is a bug in "
                        "the problem package backend." % (backend,))
            if round:
                problem.contest = round.contest
                problem.save()
                pi = ProblemInstance(contest=round.contest, round=round,
                        problem=problem, submissions_limit=submissions_limit)
                pi.save()
        self.message_user(request, _("Problem package uploaded."))
        return self.redirect_to_list(request, problem)

    def add_view(self, request, form_url='', extra_context=None):
        contest_id = request.REQUEST.get('contest_id')
        if contest_id:
            contest = get_object_or_404(Contest, id=contest_id)
        else:
            contest = None

        if not contest and \
                not request.user.has_perm('problems.problems_db_admin'):
            if getattr(request, 'contest'):
                contest = request.contest
            else:
                raise PermissionDenied

        if contest and not request.user.has_perm('contests.contest_admin',
                contest):
            raise PermissionDenied

        initial = {'contest_id': contest and contest.id or ''}

        if request.method == 'POST':
            form = ProblemUploadForm(contest, request.POST, request.FILES,
                    initial=initial)
            if form.is_valid():
                try:
                    if contest:
                        round = get_object_or_404(Round, contest=contest,
                                id=form.cleaned_data['round_id'])
                    else:
                        round = None
                    return self._add_problem(request, round,
                        form.cleaned_data['submissions_limit'])
                except Exception, e:
                    logger.error("Error processing package", exc_info=True)
                    form._errors['__all__'] = form.error_class([unicode(e)])
        else:
            form = ProblemUploadForm(contest, initial=initial)

        return TemplateResponse(request, 'admin/problems/problem_add.html',
                {'form': form})

    def _reupload_problem(self, request, problem):
        uploaded_file = request.FILES['package_file']
        with uploaded_file_name(uploaded_file) as filename:
            backend = backend_for_package(filename,
                    original_filename=uploaded_file.name)
            problem = backend.unpack(filename,
                    original_filename=uploaded_file.name,
                    existing_problem=problem)
        self.message_user(request, _("Problem updated."))
        return self.redirect_to_list(request, problem)

    def reupload_view(self, request, object_id):
        problem = self.get_object(request, unquote(object_id))
        if not problem:
            raise Http404
        if not self.has_change_permission(request, problem):
            raise PermissionDenied

        if request.method == 'POST':
            form = ProblemUploadForm(None, request.POST, request.FILES)
            if form.is_valid():
                try:
                    return self._reupload_problem(request, problem)
                except Exception, e:
                    logger.error("Error processing package", exc_info=True)
                    form._errors['__all__'] = form.error_class([unicode(e)])
        else:
            form = ProblemUploadForm(None)

        context = {
                'form': form,
                'problem': problem,
            }
        return TemplateResponse(request,
                'admin/problems/problem_reupload.html', context)

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
            url(r'^(\d+)/reupload/$', self.reupload_view,
                name='problems_problem_reupload'),
            url(r'^(\d+)/download/$', self.download_view,
                name='problems_problem_download')
        )
        return extra_urls + urls

admin.site.register(Problem, BaseProblemAdmin)
