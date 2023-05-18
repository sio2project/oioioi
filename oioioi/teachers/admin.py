from functools import partial

from django.conf import settings
from django.contrib.auth.models import User
from django.forms.models import modelform_factory
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.menu import personal_menu_registry
from oioioi.base.permissions import is_superuser
from oioioi.contests.admin import ContestAdmin
from oioioi.teachers.forms import TeacherContestForm, AddTeacherForm
from oioioi.teachers.models import ContestTeacher, RegistrationConfig, Teacher


class TeacherAdmin(admin.ModelAdmin):
    list_display = ['teacher_login', 'teacher_email', 'teacher_first_name', 'teacher_last_name', 'school', 'is_active', 'join_date']
    list_editable = ['is_active']   

    search_fields = ['school', 'user__username', 'user__first_name', 'user__last_name', 'user__email', 'join_date']

    form = AddTeacherForm

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            kwargs['queryset'] = User.objects.all().order_by('username')
        return super(TeacherAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def get_custom_list_select_related(self):
        return super(TeacherAdmin, self).get_custom_list_select_related() + ['user']

    def teacher_first_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.first_name

    def teacher_last_name(self, instance):
        if not instance.user:
            return ''
        return instance.user.last_name

    def teacher_email(self, instance):
        if not instance.user:
            return ''
        return instance.user.email

    def teacher_login(self, instance):
        if not instance.user:
            return ''
        return instance.user.get_username()

    teacher_first_name.short_description = _("First name")
    teacher_last_name.short_description = _("Last name")
    teacher_email.short_description = _("Email address")
    teacher_login.short_description = _("Username")


admin.site.register(Teacher, TeacherAdmin)

admin.system_admin_menu_registry.register(
    'teachers',
    _("Teachers"),
    lambda request: reverse('oioioiadmin:teachers_teacher_changelist'),
    condition=is_superuser,
    order=20,
)


class ContestAdminMixin(object):
    """Adjusts contest admin panel for teachers app usage. Superusers continue
    to work as usual but teachers have special options.
    """

    def has_add_permission(self, request):
        if request.user.has_perm('teachers.teacher'):
            return True
        return super(ContestAdminMixin, self).has_add_permission(request)

    def save_model(self, request, obj, form, change):
        # Superusers are allowed to add contest of any type.
        # Teachers may only add TeacherContests. The type should be
        # set only if the contest is created - if it's modified we
        # don't want to change the current type.
        if request.user.has_perm('teachers.teacher') and (
            not change and not request.user.is_superuser
        ):
            obj.controller_name = 'oioioi.teachers.controllers.TeacherContestController'
        super(ContestAdminMixin, self).save_model(request, obj, form, change)
        if not change and request.user.has_perm('teachers.teacher'):
            try:
                teacher_obj = Teacher.objects.get(user=request.user)
                ContestTeacher.objects.get_or_create(contest=obj, teacher=teacher_obj)
                RegistrationConfig.objects.get_or_create(contest=obj)
            except Teacher.DoesNotExist:
                pass

    def get_fieldsets(self, request, obj=None):
        if (
            obj
            or request.user.is_superuser
            or not request.user.has_perm('teachers.teacher')
        ):
            return super(ContestAdminMixin, self).get_fieldsets(request, obj)
        fields = list(TeacherContestForm().base_fields.keys())
        return [(None, {'fields': fields})]

    def get_form(self, request, obj=None, **kwargs):
        if (
            obj
            or request.user.is_superuser
            or not request.user.has_perm('teachers.teacher')
        ):
            return super(ContestAdminMixin, self).get_form(request, obj, **kwargs)
        return modelform_factory(
            self.model,
            form=TeacherContestForm,
            formfield_callback=partial(self.formfield_for_dbfield, request=request),
        )

    def response_add(self, request, obj, post_url_continue=None):
        if request.user.is_superuser or not request.user.has_perm('teachers.teacher'):
            return super(ContestAdminMixin, self).response_add(
                request, obj, post_url_continue
            )
        self.message_user(request, _("Contest added successfully."))
        return redirect('show_members', contest_id=obj.id, member_type='pupil')

    def __init__(self, *args, **kwargs):
        super(ContestAdminMixin, self).__init__(*args, **kwargs)


ContestAdmin.mix_in(ContestAdminMixin)

if 'oioioi.simpleui' not in settings.INSTALLED_APPS:
    personal_menu_registry.register(
        'create_contest',
        _("New contest"),
        lambda request: reverse('oioioiadmin:contests_contest_add'),
        lambda request: request.user.has_perm('teachers.teacher'),
        order=10,
    )
else:
    personal_menu_registry.register(
        'teacher_dashboard',
        _("Contests"),
        lambda request: reverse('teacher_dashboard'),
        lambda request: request.user.has_perm('teachers.teacher'),
        order=5,
    )
