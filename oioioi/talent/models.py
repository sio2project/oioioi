from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies


check_django_app_dependencies(__name__, ['oioioi.phase'])
check_django_app_dependencies(__name__, ['oioioi.supervision'])
check_django_app_dependencies(__name__, ['oioioi.scoresreveal'])

class TalentRegistrationSwitch(models.Model):
    status = models.BooleanField(default=True, verbose_name=_("status"))
