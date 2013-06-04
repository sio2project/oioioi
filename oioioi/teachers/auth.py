from django.utils.translation import ugettext_lazy as _

from oioioi.teachers.models import Teacher, ContestTeacher


class TeacherAuthBackend(object):
    description = _("Teachers permissions")
    supports_authentication = False

    def authenticate(self, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated() or not user_obj.is_active:
            return False
        if perm == 'teachers.teacher':
            return bool(Teacher.objects.filter(user=user_obj, is_active=True))
        if perm == 'contests.contest_admin' and obj is not None:
            return bool(ContestTeacher.objects.filter(teacher__user=user_obj,
                teacher__is_active=True, contest=obj))
