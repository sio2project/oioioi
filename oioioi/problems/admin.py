import logging

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.util import unquote
from django.conf.urls import patterns, url

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import is_contest_admin
from oioioi.problems.models import Problem, ProblemStatement, \
        ProblemAttachment
from oioioi.problems.utils import can_add_problems, can_change_problem


logger = logging.getLogger(__name__)


class StatementInline(admin.TabularInline):
    model = ProblemStatement
    can_delete = False
    readonly_fields = ['language', 'content_link']
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def content_link(self, instance):
        href = reverse('oioioi.problems.views.show_statement_view',
                kwargs={'statement_id': str(instance.id)})
        return make_html_link(href, instance.content.name)
    content_link.short_description = _("Content file")


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
    content_link.short_description = _("Content file")


class ProblemInstanceInline(admin.StackedInline):
    model = ProblemInstance
    can_delete = False
    fields = ['submissions_limit']
    inline_classes = ('collapse open',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class ProblemAdmin(admin.ModelAdmin):
    inlines = [StatementInline, AttachmentInline, ProblemInstanceInline]
    readonly_fields = ['name', 'short_name', 'controller_name',
            'package_backend_name']
    exclude = ['contest']
    list_filter = ['short_name']

    def has_add_permission(self, request):
        return can_add_problems(request)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return self.queryset(request).exists()
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
        if is_contest_admin(request):
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

    def _mixins_for_instance(self, request, instance=None):
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
