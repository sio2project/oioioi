# coding: utf-8
from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies

from oioioi.participants.models import RegistrationModel

check_django_app_dependencies(__name__, ['oioioi.participants'])


class MPRegistration(RegistrationModel):
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)

    def erase_data(self):
        self.terms_accepted = False
        self.save()