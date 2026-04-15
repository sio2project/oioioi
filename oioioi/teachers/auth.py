from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import (
    Q_always_false,
    Q_always_true,
)
from oioioi.contests.models import Contest
from oioioi.teachers.models import ContestTeacher, Teacher


class TeacherAuthBackend:
    description = _("Teachers permissions")
    supports_authentication = False

    def authenticate(self, request, **kwargs):
        return None

    def _is_teacher(self, user_obj):
        if not hasattr(user_obj, "_is_teacher"):
            user_obj._is_teacher = Teacher.objects.filter(user=user_obj, is_active=True).exists()
        return user_obj._is_teacher

    def _get_teachers_perm_cache(self, user_obj):
        if not hasattr(user_obj, "_teacher_perms_cache"):
            if not self._is_teacher(user_obj):
                user_obj._teacher_perms_cache = set()
            else:
                user_obj._teacher_perms_cache = set(
                    ContestTeacher.objects.filter(teacher__user=user_obj, teacher__is_active=True).values_list("contest", flat=True)
                )
        return user_obj._teacher_perms_cache

    def filter_for_perm(self, obj_class, perm, user):
        if not user.is_authenticated or not user.is_active:
            return Q_always_false()
        if user.is_superuser:
            return Q_always_true()
        if perm == "teachers.teacher":
            raise ValueError("teachers.teacher is not a per-object permission")
        if (perm == "contests.contest_admin" or perm == "contests.contest_basicadmin") and obj_class is Contest:
            return Q(id__in=self._get_teachers_perm_cache(user))
        return Q_always_false()

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active:
            return False
        if perm == "teachers.teacher":
            return self._is_teacher(user_obj)
        if (perm == "contests.contest_admin" or perm == "contests.contest_basicadmin") and isinstance(obj, Contest):
            return obj.id in self._get_teachers_perm_cache(user_obj)
