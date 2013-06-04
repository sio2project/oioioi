from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Contest
import hashlib
import random


class Teacher(models.Model):
    user = models.OneToOneField(User, primary_key=True, verbose_name=_("user"))
    is_active = models.BooleanField(default=False, verbose_name=_("active"))
    school = models.CharField(max_length=255, verbose_name=_("school"))

    class Meta:
        permissions = (
            ('teacher', _("Is a teacher")),
        )

    def __unicode__(self):
        return unicode(self.user)


class ContestTeacher(models.Model):
    contest = models.ForeignKey(Contest)
    teacher = models.ForeignKey(Teacher)

    class Meta:
        unique_together = ('contest', 'teacher')

    def __unicode__(self):
        return u'%s/%s' % (self.contest_id, self.teacher.user)


class RegistrationConfig(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True)
    is_active = models.BooleanField(default=True)
    key = models.CharField(max_length=40)

    def save(self, *args, **kwargs):
        if not self.key:
            self.generate_key()
        super(RegistrationConfig, self).save(*args, **kwargs)

    def generate_key(self):
        data = str(random.random()) + str(self.contest_id)
        self.key = hashlib.sha1(data).hexdigest()
