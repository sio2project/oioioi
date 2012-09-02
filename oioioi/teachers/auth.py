from oioioi.teachers.models import Teacher, ContestTeacher

class TeacherAuthBackend(object):
    def authenticate(self, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated():
            return False
        if perm == 'teachers.teacher':
            return bool(Teacher.objects.filter(user=user_obj, is_active=True))
        if perm == 'contests.contest_admin' and obj is not None:
            return bool(ContestTeacher.objects.filter(teacher__user=user_obj,
                teacher__is_active=True, contest=obj))

