import logging
import urllib

from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.util import unquote
from django.contrib.admin.actions import delete_selected
from django.contrib import messages
from django.conf.urls import patterns, url
from django.utils.encoding import force_unicode

from oioioi.base import admin
from oioioi.base.utils import make_html_link, make_html_links
from oioioi.base.admin import system_admin_menu_registry
from oioioi.base.permissions import make_request_condition, is_superuser
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.models import ProblemInstance, ProblemStatementConfig
from oioioi.contests.utils import is_contest_admin
from oioioi.problems.models import Problem, ProblemStatement, \
        ProblemAttachment, ProblemPackage, ProblemSite, MainProblemInstance, \
        Tag
from oioioi.problems.utils import can_add_problems, can_admin_problem
from oioioi.problems.forms import ProblemStatementConfigForm, \
        ProblemSiteForm, TagThroughForm


logger = logging.getLogger(__name__)


class StatementConfigInline(admin.TabularInline):
    model = ProblemStatementConfig
    extra = 1
    form = ProblemStatementConfigForm


class StatementConfigAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(StatementConfigAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [StatementConfigInline]
ContestAdmin.mix_in(StatementConfigAdminMixin)


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
        if instance.id is not None:
            href = reverse('oioioi.problems.views.show_statement_view',
                    kwargs={'statement_id': str(instance.id)})
            return make_html_link(href, instance.content.name)
        return None
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
        if instance.id is not None:
            href = reverse(
                'oioioi.problems.views.show_problem_attachment_view',
                kwargs={'attachment_id': str(instance.id)})
            return make_html_link(href, instance.content.name)
        return None
    content_link.short_description = _("Content file")


class ProblemInstanceInline(admin.StackedInline):
    model = ProblemInstance
    can_delete = False
    fields = []
    inline_classes = ('collapse open',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProblemSiteInline(admin.StackedInline):
    model = ProblemSite
    form = ProblemSiteForm

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class TagInline(admin.StackedInline):
    model = Tag.problems.through
    form = TagThroughForm
    extra = 0
    verbose_name = _("Tag")
    verbose_name_plural = _("Tags")

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class ProblemAdmin(admin.ModelAdmin):
    inlines = [TagInline, StatementInline, AttachmentInline,
               ProblemInstanceInline, ProblemSiteInline]
    readonly_fields = ['author', 'name', 'short_name', 'controller_name',
            'package_backend_name', 'main_problem_instance']
    exclude = ['contest']
    list_filter = ['short_name']

    def has_add_permission(self, request):
        return can_add_problems(request)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return self.get_queryset(request).exists()
        if can_admin_problem(request, obj):
            return True
        return can_admin_problem(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def redirect_to_list(self, request, problem):
        if problem.contest:
            return redirect('oioioiadmin:contests_probleminstance_changelist')
        else:
            return redirect('oioioiadmin:problems_problem_changelist')

    def response_change(self, request, obj):
        if not '_continue' in request.POST and obj.problemsite:
            return redirect('problem_site', obj.problemsite.url_key)
        else:
            return super(ProblemAdmin, self). \
                response_change(request, obj)

    def add_view(self, request, form_url='', extra_context=None):
        return redirect('add_or_update_problem',
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

    def get_queryset(self, request):
        queryset = super(ProblemAdmin, self).get_queryset(request)
        if request.user.is_anonymous():
            combined = queryset.none()
        else:
            combined = request.user.problem_set.all()
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


@make_request_condition
def pending_packages(request):
    return ProblemPackage.objects.filter(status__in=['?', 'ERR']).exists()


@make_request_condition
def pending_contest_packages(request):
    if not request.contest:
        return False
    return ProblemPackage.objects.filter(contest=request.contest,
            status__in=['?', 'ERR']).exists()


class ProblemPackageAdmin(admin.ModelAdmin):
    list_display = ['contest', 'problem_name', 'colored_status', 'package',
            'created_by', 'creation_date', 'celery_task_id', 'info']
    list_filter = ['status', 'problem_name', 'contest', 'created_by']
    actions = ['delete_selected']  # This allows us to override the action

    def __init__(self, *args, **kwargs):
        super(ProblemPackageAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = [None]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return (not obj) or (obj.status != 'OK')

    def delete_selected(self, request, queryset):
        # We use processed ProblemPackage instances to store orignal package
        # files.
        if queryset.filter(status='OK').exists():
            messages.error(request,
                    _("Cannot delete a processed Problem Package"))
        else:
            return delete_selected(self, request, queryset)
    delete_selected.short_description = (_("Delete selected %s") %
            ProblemPackage._meta.verbose_name_plural.title())

    def colored_status(self, instance):
        status_to_str = {'OK': 'ok', '?': 'in_prog', 'ERR': 'err'}
        package_status = status_to_str[instance.status]
        return '<span class="subm_admin prob_pack_%s">%s</span>' % \
                (package_status, force_unicode(instance.get_status_display()))
    colored_status.allow_tags = True
    colored_status.short_description = _("Status")
    colored_status.admin_order_field = 'status'

    def package(self, instance):
        if instance.package_file:
            href = reverse(
                    'oioioi.problems.views.download_problem_package_view',
                    kwargs={'package_id': str(instance.id)})
            return make_html_link(href, instance.package_file)
        return None
    package.short_description = _("Package file")

    def came_from(self):
        return reverse('oioioiadmin:problems_problempackage_changelist')

    def inline_actions(self, instance, contest):
        actions = []
        if instance.status == 'OK' and instance.problem:
            problem = instance.problem
            if (not problem.contest) or (problem.contest == contest):
                problem_view = reverse(
                        'oioioiadmin:problems_problem_change',
                        args=(problem.id,)) + '?' + urllib.urlencode(
                                {'came_from': self.came_from()})
                actions.append((problem_view, _("Edit problem")))
        if instance.status == 'ERR' and instance.traceback:
            traceback_view = reverse(
                    'oioioi.problems.views.download_package_traceback_view',
                    kwargs={'package_id': str(instance.id)})
            actions.append((traceback_view, _("Error details")))
        return actions

    def actions_field(self, contest):
        def inner(instance):
            inline_actions = self.inline_actions(instance, contest)
            return make_html_links(inline_actions)
        inner.allow_tags = True
        inner.short_description = _("Actions")
        return inner

    def get_list_display(self, request):
        return super(ProblemPackageAdmin, self).get_list_display(request) \
                + [self.actions_field(request.contest)]

    def get_list_select_related(self):
        return super(ProblemPackageAdmin, self).get_list_select_related() \
                + ['problem', 'problem__contest']

admin.site.register(ProblemPackage, ProblemPackageAdmin)

system_admin_menu_registry.register('problempackage_change',
        _("Problem packages"),
        lambda request:
            reverse('oioioiadmin:problems_problempackage_changelist'),
        condition=pending_packages,
        order=70)


class ContestProblemPackage(ProblemPackage):
    class Meta(object):
        proxy = True
        verbose_name = _("Contest Problem Package")


class ContestProblemPackageAdmin(ProblemPackageAdmin):
    list_display = [x for x in ProblemPackageAdmin.list_display
            if x not in ['contest', 'celery_task_id']]
    list_filter = [x for x in ProblemPackageAdmin.list_filter
            if x != 'contest']

    def get_queryset(self, request):
        qs = super(ContestProblemPackageAdmin, self).get_queryset(request)
        return qs.filter(contest=request.contest)

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def came_from(self):
        return reverse('oioioiadmin:problems_contestproblempackage_changelist')

    def get_actions(self, request):
        actions = super(ContestProblemPackageAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

contest_site.contest_register(ContestProblemPackage,
        ContestProblemPackageAdmin)
contest_admin_menu_registry.register('problempackage_change',
        _("Problem packages"),
        lambda request:
            reverse('oioioiadmin:problems_contestproblempackage_changelist'),
        condition=((~is_superuser) & pending_contest_packages),
        order=70)


class MainProblemInstanceAdmin(admin.ModelAdmin):
    fields = ['submissions_limit']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return False
        problem = obj.problem
        if problem.main_problem_instance != obj:
            return False
        return can_admin_problem(request, problem)

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        if not '_continue' in request.POST:
            return redirect('problem_site', obj.problem.problemsite.url_key)
        else:
            return super(MainProblemInstanceAdmin, self). \
                response_change(request, obj)

admin.site.register(MainProblemInstance, MainProblemInstanceAdmin)
