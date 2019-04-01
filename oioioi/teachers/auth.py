from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest
from oioioi.teachers.models import ContestTeacher, Teacher


class TeacherAuthBackend(object):
    description = _("Teachers permissions")
    supports_authentication = False

    def authenticate(self, **kwargs):
        return None

    def filter_for_perm(self, obj_class, perm, user):
        if not user.is_authenticated or not user.is_active:
            return Q(pk__isnull=True)  # (False)
        if user.is_superuser:
            return Q(pk__isnull=False)  # (True)
        if perm == 'teachers.teacher':
            raise ValueError("teachers.teacher is not a per-object permission")
        if perm == 'contests.contest_admin' and obj_class is Contest:
            return Q(contestteacher__teacher__user=user, contestteacher__teacher__is_active=True)
        return Q(pk__isnull=True)  # (False)

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active:
            return False
        if perm == 'teachers.teacher':
            if not hasattr(user_obj, '_is_teacher'):
                user_obj._is_teacher = Teacher.objects.filter(
                    user=user_obj, is_active=True).exists()
            return user_obj._is_teacher
        if perm == 'contests.contest_admin' and isinstance(obj, Contest):
            if not hasattr(user_obj, '_teacher_perms_cache'):
                user_obj._teacher_perms_cache = set(ContestTeacher.objects
                    .filter(teacher__user=user_obj, teacher__is_active=True)
                    .values_list('contest', flat=True))
            return obj.id in user_obj._teacher_perms_cache
