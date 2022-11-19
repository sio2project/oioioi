from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import generate_key
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Contest

check_django_app_dependencies(__name__, ['oioioi.participants'])

if 'oioioi.teachers.auth.TeacherAuthBackend' not in settings.AUTHENTICATION_BACKENDS:
    raise ImproperlyConfigured(
        "When using teacher module you have to activate TeacherAuthBackend"
    )



class Teacher(models.Model):
    user = models.OneToOneField(
        User, primary_key=True, verbose_name=_("user"), on_delete=models.CASCADE
    )
    is_active = models.BooleanField(default=False, verbose_name=_("active"))
    school = models.CharField(max_length=255, verbose_name=_("school"))

    class Meta(object):
        permissions = (('teacher', _("Is a teacher")),)

    def __str__(self):
        return str(self.user)



class ContestTeacher(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)

    class Meta(object):
        unique_together = ('contest', 'teacher')

    def __str__(self):
        return u'%s/%s' % (self.contest_id, self.teacher.user)


class RegistrationConfig(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True, on_delete=models.CASCADE)
    is_active_pupil = models.BooleanField(default=True)
    is_active_teacher = models.BooleanField(default=True)
    pupil_key = models.CharField(max_length=40)
    teacher_key = models.CharField(max_length=40)

    def __init__(self, *args, **kwargs):
        super(RegistrationConfig, self).__init__(*args, **kwargs)
        if not self.teacher_key:
            self.teacher_key = generate_key()
        if not self.pupil_key:
            self.pupil_key = generate_key()
