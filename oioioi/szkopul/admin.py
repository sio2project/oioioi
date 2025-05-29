from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.participants.admin import ParticipantAdmin
from oioioi.szkopul.forms import MAPCourseRegistrationForm
from oioioi.szkopul.models import MAPCourseRegistration


class MAPCourseRegistrationInline(admin.StackedInline):
    model = MAPCourseRegistration
    fk_name = 'participant'
    form = MAPCourseRegistrationForm
    can_delete = False
    inline_classes = ('collapse open',)
    # We don't allow admins to change users' acceptance of contest's terms.
    exclude = ('terms_accepted',)


class MAPCourseRegistrationParticipantAdmin(ParticipantAdmin):
    # list_display = ParticipantAdmin.list_display + [
    #     'not_primaryschool',
    # ]
    inlines = tuple(ParticipantAdmin.inlines) + (MAPCourseRegistrationInline,)
    readonly_fields = ['user']

    # def get_custom_list_select_related(self):
    #     return super(
    #         MAPCourseRegistrationParticipantAdmin, self
    #     ).get_custom_list_select_related() + [
    #         'szkopul_mapcourseregistration',
    #         'szkopul_mapcourseregistration__school',
    #     ]

    # def school_name(self, instance):
    #     if instance.szkopul_mapcourseregistration.school is None:
    #         return _("-- school deleted --")
    #     return instance.szkopul_mapcourseregistration.school.name

    # school_name.short_description = _("School")
    # school_name.admin_order_field = 'szkopul_mapcourseregistration__school__name'

    # def school_city(self, instance):
    #     if instance.szkopul_mapcourseregistration.school is None:
    #         return ''
    #     return instance.szkopul_mapcourseregistration.school.city

    # school_city.admin_order_field = 'szkopul_mapcourseregistration__school__city'

    # def school_province(self, instance):
    #     if instance.szkopul_mapcourseregistration.school is None:
    #         return ''
    #     return instance.szkopul_mapcourseregistration.school.province

    # school_province.admin_order_field = 'szkopul_mapcourseregistration__school__province'

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj = None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super(MAPCourseRegistrationParticipantAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
