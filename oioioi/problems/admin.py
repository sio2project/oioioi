import logging

import urllib.parse

from django.contrib import messages
from django.contrib.admin.actions import delete_selected
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import re_path, reverse
from django.utils.html import escape, format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from oioioi.base import admin
from oioioi.base.admin import NO_CATEGORY, system_admin_menu_registry
from oioioi.base.permissions import is_superuser, make_request_condition
from oioioi.base.utils import make_html_link, make_html_links
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import (
    ProblemInstance,
    ProblemStatementConfig,
    RankingVisibilityConfig, RegistrationAvailabilityConfig,
)
from oioioi.contests.utils import is_contest_admin, is_contest_basicadmin
from oioioi.problems.forms import (
    AlgorithmTagThroughForm,
    DifficultyTagThroughForm,
    LocalizationFormset,
    OriginInfoValueForm,
    OriginInfoValueThroughForm,
    OriginTagThroughForm,
    ProblemNameInlineFormSet,
    ProblemSiteForm,
    ProblemStatementConfigForm,
    RankingVisibilityConfigForm, RegistrationAvailabilityConfigForm,
)
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagLocalization,
    DifficultyTag,
    DifficultyTagLocalization,
    MainProblemInstance,
    OriginInfoCategory,
    OriginInfoCategoryLocalization,
    OriginInfoValue,
    OriginInfoValueLocalization,
    OriginTag,
    OriginTagLocalization,
    Problem,
    ProblemAttachment,
    ProblemName,
    ProblemPackage,
    ProblemSite,
    ProblemStatement,
)
from oioioi.problems.utils import can_add_problems, can_admin_problem

logger = logging.getLogger(__name__)


class StatementConfigInline(admin.TabularInline):
    model = ProblemStatementConfig
    extra = 1
    form = ProblemStatementConfigForm
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
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
        self.inlines = tuple(self.inlines) + (StatementConfigInline,)


ContestAdmin.mix_in(StatementConfigAdminMixin)


class RankingVisibilityConfigInline(admin.TabularInline):
    model = RankingVisibilityConfig
    extra = 1
    form = RankingVisibilityConfigForm
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)


class RankingVisibilityConfigAdminMixin(object):
    """Adds :class:`~oioioi.contests.models.RankingVisibilityConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(RankingVisibilityConfigAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (RankingVisibilityConfigInline,)


ContestAdmin.mix_in(RankingVisibilityConfigAdminMixin)


class RegistrationAvailabilityConfigInline(admin.TabularInline):
    model = RegistrationAvailabilityConfig
    extra = 1
    form = RegistrationAvailabilityConfigForm
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)


class RegistrationAvailabilityConfigAdminMixin(object):
    """Adds :class:`~oioioi.contests.models.OpenRegistrationConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(RegistrationAvailabilityConfigAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (RegistrationAvailabilityConfigInline,)


ContestAdmin.mix_in(RegistrationAvailabilityConfigAdminMixin)


class NameInline(admin.StackedInline):
    model = ProblemName
    can_delete = False
    formset = ProblemNameInlineFormSet
    fields = ['name', 'language']
    category = NO_CATEGORY

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class StatementInline(admin.TabularInline):
    model = ProblemStatement
    can_delete = False
    readonly_fields = ['language', 'content_link']
    fields = readonly_fields
    category = NO_CATEGORY

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def content_link(self, instance):
        if instance.id is not None:
            href = reverse('show_statement', kwargs={'statement_id': str(instance.id)})
            return make_html_link(href, instance.content.name)
        return None

    content_link.short_description = _("Content file")


class AttachmentInline(admin.TabularInline):
    model = ProblemAttachment
    extra = 0
    readonly_fields = ['content_link']
    category = NO_CATEGORY

    def content_link(self, instance):
        if instance.id is not None:
            href = reverse(
                'show_problem_attachment', kwargs={'attachment_id': str(instance.id)}
            )
            return make_html_link(href, instance.content.name)
        return None

    content_link.short_description = _("Content file")


class ProblemInstanceInline(admin.StackedInline):
    model = ProblemInstance
    can_delete = False
    fields = []
    inline_classes = ('collapse open',)
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProblemSiteInline(admin.StackedInline):
    model = ProblemSite
    form = ProblemSiteForm
    category = NO_CATEGORY

    def has_add_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


def tag_inline(
    model,
    form,
    verbose_name,
    verbose_name_plural,
    extra=0,
    category=_("Tags"),
    has_permission_func=lambda self, request, obj=None: True,
):
    def decorator(cls):
        cls.model = model
        cls.form = form
        cls.verbose_name = verbose_name
        cls.verbose_name_plural = verbose_name_plural
        cls.extra = extra
        cls.category = category
        cls.has_add_permission = has_permission_func
        cls.has_change_permission = has_permission_func
        cls.has_delete_permission = has_permission_func
        cls.has_view_permission = has_permission_func

        return cls

    return decorator


def _update_queryset_if_problems(db_field, **kwargs):
    if db_field.name == 'problems':
        kwargs['queryset'] = Problem.objects.filter(
            visibility=Problem.VISIBILITY_PUBLIC
        )


class BaseTagLocalizationInline(admin.StackedInline):
    formset = LocalizationFormset


class BaseTagAdmin(admin.ModelAdmin):
    filter_horizontal = ('problems',)


@tag_inline(
    model=OriginTag.problems.through,
    form=OriginTagThroughForm,
    verbose_name=_("origin tag"),
    verbose_name_plural=_("origin tags"),
    has_permission_func=lambda self, request, obj=None: request.user.is_superuser,
)
class OriginTagInline(admin.StackedInline):
    pass


class OriginTagLocalizationInline(BaseTagLocalizationInline):
    model = OriginTagLocalization


class OriginTagAdmin(BaseTagAdmin):
    inlines = (OriginTagLocalizationInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        _update_queryset_if_problems(db_field, **kwargs)
        return super(OriginTagAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


admin.site.register(OriginTag, OriginTagAdmin)


class OriginInfoCategoryLocalizationInline(BaseTagLocalizationInline):
    model = OriginInfoCategoryLocalization


class OriginInfoCategoryAdmin(admin.ModelAdmin):
    inlines = (OriginInfoCategoryLocalizationInline,)


admin.site.register(OriginInfoCategory, OriginInfoCategoryAdmin)


@tag_inline(
    model=OriginInfoValue.problems.through,
    form=OriginInfoValueThroughForm,
    verbose_name=_("origin information"),
    verbose_name_plural=_("additional origin information"),
    has_permission_func=lambda self, request, obj=None: request.user.is_superuser,
)
class OriginInfoValueInline(admin.StackedInline):
    pass


class OriginInfoValueLocalizationInline(BaseTagLocalizationInline):
    model = OriginInfoValueLocalization


class OriginInfoValueAdmin(admin.ModelAdmin):
    form = OriginInfoValueForm
    inlines = (OriginInfoValueLocalizationInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        _update_queryset_if_problems(db_field, **kwargs)
        return super(OriginInfoValueAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


admin.site.register(OriginInfoValue, OriginInfoValueAdmin)


@tag_inline(
    model=DifficultyTag.problems.through,
    form=DifficultyTagThroughForm,
    verbose_name=_("Difficulty Tag"),
    verbose_name_plural=_("Difficulty Tags"),
)
class DifficultyTagInline(admin.StackedInline):
    pass


class DifficultyTagLocalizationInline(BaseTagLocalizationInline):
    model = DifficultyTagLocalization


class DifficultyTagAdmin(BaseTagAdmin):
    inlines = (DifficultyTagLocalizationInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        _update_queryset_if_problems(db_field, **kwargs)
        return super(DifficultyTagAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


admin.site.register(DifficultyTag, DifficultyTagAdmin)


@tag_inline(
    model=AlgorithmTag.problems.through,
    form=AlgorithmTagThroughForm,
    verbose_name=_("Algorithm Tag"),
    verbose_name_plural=_("Algorithm Tags"),
)
class AlgorithmTagInline(admin.StackedInline):
    pass


class AlgorithmTagLocalizationInline(BaseTagLocalizationInline):
    model = AlgorithmTagLocalization


class AlgorithmTagAdmin(BaseTagAdmin):
    inlines = (AlgorithmTagLocalizationInline,)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        _update_queryset_if_problems(db_field, **kwargs)
        return super(AlgorithmTagAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


admin.site.register(AlgorithmTag, AlgorithmTagAdmin)


class ProblemAdmin(admin.ModelAdmin):
    inlines = (
        DifficultyTagInline,
        AlgorithmTagInline,
        OriginTagInline,
        OriginInfoValueInline,
        NameInline,
        StatementInline,
        AttachmentInline,
        ProblemInstanceInline,
        ProblemSiteInline,
    )
    readonly_fields = [
        'author',
        'legacy_name',
        'short_name',
        'controller_name',
        'package_backend_name',
        'main_problem_instance',
        'ascii_name',
    ]
    exclude = ['contest']
    list_filter = ['short_name']

    class Media(object):
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
            return redirect('oioioiadmin:contests_probleminstance_changelist', contest_id=problem.contest.id)
        else:
            return redirect('problemset_all_problems')

    def response_change(self, request, obj):
        if '_continue' not in request.POST and obj.problemsite:
            return redirect('problem_site', obj.problemsite.url_key)
        else:
            return super(ProblemAdmin, self).response_change(request, obj)

    def add_view(self, request, form_url='', extra_context=None):
        if request.contest:
            return redirect('add_or_update_problem', contest_id=request.contest.id)
        else:
            return redirect('add_or_update_problem')

    def download_view(self, request, object_id):
        problem = self.get_object(request, unquote(object_id))
        if not problem:
            raise Http404
        if not self.has_change_permission(request, problem):
            raise PermissionDenied
        try:
            return problem.package_backend.pack(problem)
        except NotImplementedError:
            self.message_user(
                request, _("Package not available for problem %s.") % (problem,)
            )
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
        response = super(ProblemAdmin, self).delete_view(
            request, object_id, extra_context
        )
        if isinstance(response, HttpResponseRedirect):
            return self.redirect_to_list(request, obj)
        return response

    def get_readonly_fields(self, request, obj=None):
        if not (request.user.is_superuser or is_contest_admin(request)):
            return ['visibility'] + self.readonly_fields
        return self.readonly_fields

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['categories'] = sorted(
            set([getattr(inline, 'category', None) for inline in self.inlines])
        )
        extra_context['no_category'] = NO_CATEGORY
        return super(ProblemAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context
        )


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
            re_path(
                r'^(\d+)/download/$',
                self.download_view,
                name='problems_problem_download',
            )
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
    return ProblemPackage.objects.filter(
        contest=request.contest, status__in=['?', 'ERR']
    ).exists()


class ProblemPackageAdmin(admin.ModelAdmin):
    list_display = [
        'contest',
        'problem_name',
        'colored_status',
        'created_by',
        'creation_date',
        'package_info',
    ]
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

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return (not obj) or (obj.status != 'OK')

    def delete_selected(self, request, queryset):
        # We use processed ProblemPackage instances to store orignal package
        # files.
        if queryset.filter(status='OK').exists():
            messages.error(request, _("Cannot delete a processed Problem Package"))
        else:
            return delete_selected(self, request, queryset)

    delete_selected.short_description = (
        _("Delete selected %s") % ProblemPackage._meta.verbose_name_plural.title()
    )

    def colored_status(self, instance):
        status_to_str = {'OK': 'ok', '?': 'in_prog', 'ERR': 'err'}
        package_status = status_to_str[instance.status]
        return format_html(
            u'<span class="submission-admin prob-pack--{}">{}</span>',
            package_status,
            instance.get_status_display(),
        )

    colored_status.short_description = _("Status")
    colored_status.admin_order_field = 'status'

    def package_info(self, instance):
        if instance.info:
            return mark_safe(escape(instance.info).replace("\n", "<br>"))
        else:
            return "-"

    package_info.short_description = _("Package information")

    def came_from(self):
        return reverse('oioioiadmin:problems_problempackage_changelist')

    def inline_actions(self, instance, contest):
        actions = []
        if instance.package_file:
            package_download = reverse(
                'download_package', kwargs={'package_id': str(instance.id)}
            )
            actions.append((package_download, _("Package download")))
        if instance.status == 'OK' and instance.problem:
            problem = instance.problem
            if (not problem.contest) or (problem.contest == contest):
                problem_view = (
                    reverse('oioioiadmin:problems_problem_change', args=(problem.id,))
                    + '?'
                    + urllib.parse.urlencode({'came_from': self.came_from()})
                )
                actions.append((problem_view, _("Edit problem")))
        if instance.status == 'ERR' and instance.traceback:
            traceback_view = reverse(
                'download_package_traceback', kwargs={'package_id': str(instance.id)}
            )
            actions.append((traceback_view, _("Error details")))
        return actions

    def actions_field(self, contest):
        def inner(instance):
            inline_actions = self.inline_actions(instance, contest)
            return make_html_links(inline_actions)

        inner.short_description = _("Actions")
        return inner

    def get_list_display(self, request):
        items = super(ProblemPackageAdmin, self).get_list_display(request) + [
            self.actions_field(request.contest)
        ]
        if not is_contest_admin(request):
            disallowed_items = ['created_by', 'actions_field']
            items = [item for item in items if item not in disallowed_items]
        return items

    def get_list_filter(self, request):
        items = super(ProblemPackageAdmin, self).get_list_filter(request)
        if not is_contest_admin(request):
            disallowed_items = ['created_by']
            items = [item for item in items if item not in disallowed_items]
        return items

    def get_custom_list_select_related(self):
        return super(ProblemPackageAdmin, self).get_custom_list_select_related() + [
            'problem',
            'problem__contest',
        ]


admin.site.register(ProblemPackage, ProblemPackageAdmin)

system_admin_menu_registry.register(
    'problempackage_change',
    _("Problem packages"),
    lambda request: reverse('oioioiadmin:problems_problempackage_changelist'),
    condition=pending_packages,
    order=70,
)


class ContestProblemPackage(ProblemPackage):
    class Meta(object):
        proxy = True
        verbose_name = _("Contest Problem Package")


class ContestProblemPackageAdmin(ProblemPackageAdmin):
    list_display = [
        x
        for x in ProblemPackageAdmin.list_display
        if x not in ['contest', 'celery_task_id']
    ]
    list_filter = [x for x in ProblemPackageAdmin.list_filter if x != 'contest']

    def __init__(self, *args, **kwargs):
        super(ContestProblemPackageAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

    def get_queryset(self, request):
        qs = super(ContestProblemPackageAdmin, self).get_queryset(request)
        return qs.filter(
            Q(contest=request.contest) | Q(problem__contest=request.contest)
        )

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


contest_site.contest_register(ContestProblemPackage, ContestProblemPackageAdmin)
contest_admin_menu_registry.register(
    'problempackage_change',
    _("Problem packages"),
    lambda request: reverse('oioioiadmin:problems_contestproblempackage_changelist'),
    condition=((~is_superuser) & pending_contest_packages),
    order=70,
)


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
            return super(MainProblemInstanceAdmin, self).response_change(request, obj)


admin.site.register(MainProblemInstance, MainProblemInstanceAdmin)
