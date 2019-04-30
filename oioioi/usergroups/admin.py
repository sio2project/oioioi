import types

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.db import models

from oioioi.base import admin
from oioioi.base.permissions import is_superuser
from oioioi.usergroups.models import UserGroup, ActionConfig
from oioioi.teachers.menu import teacher_menu_registry


def get_user_name_and_login_bounded(self, user):
    return "%s (%s)" % (user.get_full_name(), user.username)

class UserGroupAdmin(admin.ModelAdmin):
    exclude = ('addition_config', 'sharing_config')
    filter_horizontal = ('owners', 'members')
    search_fields = ('name',)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super(UserGroupAdmin, self).formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name == 'owners':
            formfield.queryset = User.objects.exclude(teacher=None) | \
                                 User.objects.filter(is_superuser=True)

        if isinstance(db_field, models.ManyToManyField):
            formfield.label_from_instance = types.MethodType(get_user_name_and_login_bounded, formfield)

        return formfield

admin.site.register(UserGroup, UserGroupAdmin)

admin.system_admin_menu_registry.register('user_groups', _("User Groups"),
        lambda request: reverse('oioioiadmin:usergroups_usergroup_changelist'),
        condition=is_superuser, order=10)

teacher_menu_registry.register('user_groups', _("User Groups"),
        lambda request: reverse('teacher_usergroups_list'), order=20)