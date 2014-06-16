from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Contest
import hashlib
import random


check_django_app_dependencies(__name__, ['oioioi.participants'])


class Teacher(models.Model):
    user = models.OneToOneField(User, primary_key=True, verbose_name=_("user"))
    is_active = models.BooleanField(default=False, verbose_name=_("active"))
    school = models.CharField(max_length=255, verbose_name=_("school"))

    class Meta(object):
        permissions = (
            ('teacher', _("Is a teacher")),
        )

    def __unicode__(self):
        return unicode(self.user)


class ContestTeacher(models.Model):
    contest = models.ForeignKey(Contest)
    teacher = models.ForeignKey(Teacher)

    class Meta(object):
        unique_together = ('contest', 'teacher')

    def __unicode__(self):
        return u'%s/%s' % (self.contest_id, self.teacher.user)


class RegistrationConfig(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True)
    is_active_pupil = models.BooleanField(default=True)
    is_active_teacher = models.BooleanField(default=True)
    pupil_key = models.CharField(max_length=40)
    teacher_key = models.CharField(max_length=40)

    def __init__(self, *args, **kwargs):
        super(RegistrationConfig, self).__init__(*args, **kwargs)
        if self.contest:
            if not self.teacher_key:
                self.teacher_key = self.generate_key()
            if not self.pupil_key:
                self.pupil_key = self.generate_key()

    def generate_key(self):
        data = str(random.random()) + str(self.contest_id)
        return hashlib.sha1(data).hexdigest()
