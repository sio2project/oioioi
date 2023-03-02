from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Contest


check_django_app_dependencies(__name__, ['oioioi.phase'])
check_django_app_dependencies(__name__, ['oioioi.supervision'])
check_django_app_dependencies(__name__, ['oioioi.scoresreveal'])

class TalentRegistrationSwitch(models.Model):
    status = models.BooleanField(default=True, verbose_name=_("status"))

class TalentRegistration(models.Model):
    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, verbose_name=_("contest"), on_delete=models.CASCADE)
    
    class Meta(object):
        verbose_name = _("Talent registration")
        verbose_name_plural = _("Talent registrations")
        ordering = ['user__last_name']
    
    def __str__(self):
        return str("{} {} {}".format(self.user, _("inside"), self.contest))
