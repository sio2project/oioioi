import logging

import six.moves.urllib.parse
from django.conf.urls import url
from django.contrib import messages
from django.contrib.admin.actions import delete_selected
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from oioioi.base import admin
from oioioi.base.admin import system_admin_menu_registry
from oioioi.base.permissions import is_superuser, make_request_condition
from oioioi.base.utils import make_html_link, make_html_links
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import ProblemInstance, ProblemStatementConfig
from oioioi.contests.utils import is_contest_admin, is_contest_basicadmin
from oioioi.problems.forms import (ProblemSiteForm, ProblemStatementConfigForm,
                                   OriginTagThroughForm, OriginInfoValueForm,
                                   OriginInfoValueThroughForm,
                                   TagThroughForm, DifficultyTagThroughForm,
                                   AlgorithmTagThroughForm,
                                   LocalizationFormset)
from oioioi.problems.models import (MainProblemInstance, Problem,
                                    ProblemAttachment, ProblemPackage,
                                    ProblemSite, ProblemStatement, Tag,
                                    AlgorithmTag, DifficultyTag,
                                    OriginTag, OriginTagLocalization,
                                    OriginInfoValue,
                                    OriginInfoValueLocalization,
                                    OriginInfoCategory,
                                    OriginInfoCategoryLocalization)
from oioioi.problems.utils import can_add_problems, can_admin_problem

logger = logging.getLogger(__name__)


class StatementConfigInline(admin.TabularInline):
    model = ProblemStatementConfig
    extra = 1
    form = ProblemStatementConfigForm

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)


class StatementConfigAdminMixin(object):
    """Adds :class:`~oioioi.contests.models.ProblemStatementConfig` to an admin
       panel.
    """

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
            href = reverse('show_statement',
                    kwargs={'statement_id': str(instance.id)})
            return make_html_link(href, instance.content.name)
        return None
    content_link.short_description = _("Content file")


class AttachmentInline(admin.TabularInline):
    model = ProblemAttachment
    extra = 0
    readonly_fields = ['content_link']

    def content_link(self, instance):
        if instance.id is not None:
            href = reverse('show_problem_attachment',
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


class OriginTagLocalizationInline(admin.StackedInline):
    model = OriginTagLocalization
    formset = LocalizationFormset


class OriginTagAdmin(admin.ModelAdmin):
    filter_horizontal = ('problems',)
    inlines = (OriginTagLocalizationInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'problems':
            kwargs['queryset'] = Problem.objects \
                    .filter(visibility=Problem.VISIBILITY_PUBLIC)
        return super(OriginTagAdmin, self) \
                .formfield_for_manytomany(db_field, request, **kwargs)

admin.site.register(OriginTag, OriginTagAdmin)


class OriginInfoCategoryLocalizationInline(admin.StackedInline):
    model = OriginInfoCategoryLocalization
    formset = LocalizationFormset


class OriginInfoCategoryAdmin(admin.ModelAdmin):
    inlines = (OriginInfoCategoryLocalizationInline,)

admin.site.register(OriginInfoCategory, OriginInfoCategoryAdmin)


class OriginInfoValueLocalizationInline(admin.StackedInline):
    model = OriginInfoValueLocalization
    formset = LocalizationFormset


class OriginInfoValueAdmin(admin.ModelAdmin):
    form = OriginInfoValueForm

    filter_horizontal = ('problems',)
    inlines = (OriginInfoValueLocalizationInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'problems':
            kwargs['queryset'] = Problem.objects \
                    .filter(visibility=Problem.VISIBILITY_PUBLIC)
        return super(OriginInfoValueAdmin, self) \
                .formfield_for_manytomany(db_field, request, **kwargs)

admin.site.register(OriginInfoValue, OriginInfoValueAdmin)


class OriginTagInline(admin.StackedInline):
    model = OriginTag.problems.through
    form = OriginTagThroughForm
    extra = 0
    verbose_name = _("origin tag")
    verbose_name_plural = _("origin tags")

    # Prevent the problem owner from changing the problem's origin tags
    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class OriginInfoValueInline(admin.StackedInline):
    model = OriginInfoValue.problems.through
    form = OriginInfoValueThroughForm
    extra = 0
    verbose_name = _("origin information")
    verbose_name_plural = _("additional origin information")

    # Prevent the problem owner from changing the problem's origin meta
    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class DifficultyTagInline(admin.StackedInline):
    model = DifficultyTag.problems.through
    form = DifficultyTagThroughForm
    extra = 0
    verbose_name = _("Difficulty Tag")
    verbose_name_plural = _("Difficulty Tags")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class AlgorithmTagInline(admin.StackedInline):
    model = AlgorithmTag.problems.through
    form = AlgorithmTagThroughForm
    extra = 0
    verbose_name = _("Algorithm Tag")
    verbose_name_plural = _("Algorithm Tags")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class TagInline(admin.StackedInline):
    model = Tag.problems.through
    form = TagThroughForm
    extra = 0
    verbose_name = _("Tag (deprecated)")
    verbose_name_plural = _("Tags (deprecated)")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ProblemAdmin(admin.ModelAdmin):
    inlines = [TagInline, DifficultyTagInline, AlgorithmTagInline,
               OriginTagInline, OriginInfoValueInline,
               StatementInline, AttachmentInline,
               ProblemInstanceInline, ProblemSiteInline]
    readonly_fields = ['author', 'name', 'short_name', 'controller_name',
            'package_backend_name', 'main_problem_instance', 'ascii_name']
    exclude = ['contest']
    list_filter = ['short_name']

    class Media():
        js = ('problems/admin-origintag.js',)

    def has_add_permission(self, request):
        return can_add_problems(request)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return self.get_queryset(request).exists()
        else:
            return can_admin_problem(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def redirect_to_list(self, request, problem):
        if problem.contest:
            return redirect('oioioiadmin:contests_probleminstance_changelist')
        else:
            return redirect('oioioiadmin:problems_problem_changelist')

    def response_change(self, request, obj):
        if '_continue' not in request.POST and obj.problemsite:
            return redirect('problem_site', obj.problemsite.url_key)
        else:
            return super(ProblemAdmin, self).response_change(request, obj)

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
        if request.user.is_anonymous:
            combined = queryset.none()
        else:
            combined = request.user.problem_set.all()
        if request.user.has_perm('problems.problems_db_admin'):
            combined |= queryset.filter(contest__isnull=True)
        if is_contest_basicadmin(request):
            combined |= queryset.filter(contest=request.contest)
        return combined

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        response = super(ProblemAdmin, self).delete_view(request, object_id,
                extra_context)
        if isinstance(response, HttpResponseRedirect):
            return self.redirect_to_list(request, obj)
        return response

    def get_readonly_fields(self, request, obj=None):
        if not (request.user.is_superuser or is_contest_admin(request)):
            return ['visibility',] + self.readonly_fields
        return self.readonly_fields


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
        extra_urls = [
            url(r'^(\d+)/download/$', self.download_view,
                name='problems_problem_download')
        ]
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
    list_filter = ['status', 'problem_name', 'contest']
    actions = ['delete_selected']  # This allows us to override the action

    def __init__(self, *args, **kwargs):
        super(ProblemPackageAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

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
        return format_html(
            u'<span class="submission-admin prob-pack--{}">{}</span>',
            package_status, instance.get_status_display()
        )
    colored_status.short_description = _("Status")
    colored_status.admin_order_field = 'status'

    def package(self, instance):
        if instance.package_file:
            href = reverse('download_package',
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
                        args=(problem.id,)) + '?' + six.moves.urllib.parse.urlencode(
                                {'came_from': self.came_from()})
                actions.append((problem_view, _("Edit problem")))
        if instance.status == 'ERR' and instance.traceback:
            traceback_view = reverse('download_package_traceback',
                                     kwargs={'package_id': str(instance.id)})
            actions.append((traceback_view, _("Error details")))
        return actions

    def actions_field(self, contest):
        def inner(instance):
            inline_actions = self.inline_actions(instance, contest)
            return make_html_links(inline_actions)
        inner.short_description = _("Actions")
        return inner

    def get_list_display(self, request):
        items = super(ProblemPackageAdmin, self).get_list_display(request) \
                + [self.actions_field(request.contest)]
        if not is_contest_admin(request):
            disallowed_items = ['package', 'created_by',]
            items = [item for item in items if item not in disallowed_items]
        return items

    def get_list_filter(self, request):
        items = super(ProblemPackageAdmin, self).get_list_filter(request)
        if not is_contest_admin(request):
            disallowed_items = ['created_by',]
            items = [item for item in items if item not in disallowed_items]
        return items

    def get_custom_list_select_related(self):
        return \
            super(ProblemPackageAdmin, self).get_custom_list_select_related()\
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

    def __init__(self, *args, **kwargs):
        super(ContestProblemPackageAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

    def get_queryset(self, request):
        qs = super(ContestProblemPackageAdmin, self).get_queryset(request)
        return qs.filter(Q(contest=request.contest) |
                         Q(problem__contest=request.contest))

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return is_contest_basicadmin(request)

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
    fields = ('problem', 'short_name')
    readonly_fields = ('problem',)

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
        if '_continue' not in request.POST:
            return redirect('problem_site', obj.problem.problemsite.url_key)
        else:
            return super(MainProblemInstanceAdmin, self). \
                response_change(request, obj)

admin.site.register(MainProblemInstance, MainProblemInstanceAdmin)
