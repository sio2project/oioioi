from django.conf import settings
from django.db import models
from oioioi.participants.models import RegistrationModel
from django.utils.translation import gettext_lazy as _

class TalentRegistration(RegistrationModel):
    group_choices = list(settings.TALENT_CONTEST_NAMES.items())
    group = models.CharField(
        max_length=1,
        choices=group_choices,
        default="",
        verbose_name=_("Group"),
    )
    def erase_data(self):
        self.group=""
        self.save()
