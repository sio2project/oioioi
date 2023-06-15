import types

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.menu import personal_menu_registry
from oioioi.base.permissions import is_superuser
from oioioi.usergroups.models import UserGroup, UserGroupRanking
from oioioi.contests.admin import ContestAdmin, NO_CATEGORY


def get_user_name_and_login_bounded(self, user):
    return "%s (%s)" % (user.get_full_name(), user.username)


class UserGroupAdmin(admin.ModelAdmin):
    exclude = ('addition_config', 'sharing_config', 'contests')
    filter_horizontal = ('owners', 'members')
    search_fields = ('name',)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super(UserGroupAdmin, self).formfield_for_dbfield(
            db_field, request, **kwargs
        )

        if db_field.name == 'owners':
            formfield.queryset = User.objects.exclude(
                teacher=None
            ) | User.objects.filter(is_superuser=True)

        if isinstance(db_field, models.ManyToManyField):
            formfield.label_from_instance = types.MethodType(
                get_user_name_and_login_bounded, formfield
            )

        return formfield


admin.site.register(UserGroup, UserGroupAdmin)

admin.system_admin_menu_registry.register(
    'user_groups',
    _("User Groups"),
    lambda request: reverse('oioioiadmin:usergroups_usergroup_changelist'),
    condition=is_superuser,
    order=10,
)

personal_menu_registry.register(
    'user_groups',
    _("User Groups"),
    lambda request: reverse('teacher_usergroups_list'),
    lambda request: request.user.has_perm('teachers.teacher'),
    order=20,
)


class UserGroupRankingInline(admin.StackedInline):
    model = UserGroupRanking
    extra = 0
    category = NO_CATEGORY

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user_group':
            kwargs['queryset'] = UserGroup.objects.filter(
                contests=request.contest
            )
        return super(UserGroupRankingInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class UserGroupRankingsContestAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(UserGroupRankingsContestAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (UserGroupRankingInline,)


ContestAdmin.mix_in(UserGroupRankingsContestAdminMixin)
