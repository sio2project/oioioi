from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import (
    Q_always_false,
    Q_always_true,
)
from oioioi.contests.models import Contest
from oioioi.teachers.models import ContestTeacher, Teacher


class TeacherAuthBackend(object):
    description = _("Teachers permissions")
    supports_authentication = False

    def authenticate(self, request, **kwargs):
        return None

    def filter_for_perm(self, obj_class, perm, user):
        if not user.is_authenticated or not user.is_active:
            return Q_always_false()
        if user.is_superuser:
            return Q_always_true()
        if perm == 'teachers.teacher':
            raise ValueError("teachers.teacher is not a per-object permission")
        if (perm == 'contests.contest_admin' or perm == 'contests.contest_basicadmin') and obj_class is Contest:
            if Teacher.objects.filter(user=user, is_active=True).exists():
                return Q(
                    contestteacher__teacher__user=user,
                )

            return Q_always_false()
        return Q_always_false()

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active:
            return False
        if perm == 'teachers.teacher':
            if not hasattr(user_obj, '_is_teacher'):
                user_obj._is_teacher = Teacher.objects.filter(
                    user=user_obj, is_active=True
                ).exists()
            return user_obj._is_teacher
        if (perm == 'contests.contest_admin' or perm == 'contests.contest_basicadmin') and isinstance(obj, Contest):
            if not hasattr(user_obj, '_teacher_perms_cache'):
                user_obj._teacher_perms_cache = set(
                    ContestTeacher.objects.filter(
                        teacher__user=user_obj, teacher__is_active=True
                    ).values_list('contest', flat=True)
                )
            return obj.id in user_obj._teacher_perms_cache
