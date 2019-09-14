# coding: utf-8
from importlib import import_module

from django.conf import settings
import django.dispatch

# pylint: disable=unused-import
# Important. This import is to register signal handlers. Do not remove it.
import oioioi.base.signal_handlers
from oioioi.base.setup_check import setup_check

# Check if deployment and installation config versions match.
# Check if database settings are correct.
setup_check()

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            # Controllers should be imported at startup, because they register
            # mixins
            import_module(app + '.controllers')
        except ImportError:
            pass

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

# Sender will be equal to the form that was completed
PreferencesSaved = django.dispatch.Signal(providing_args=['user'])

class Consents(models.Model):
    user = models.OneToOneField(User, primary_key=True, verbose_name=_("user"),
                                on_delete=models.CASCADE)
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)
    marketing_consent = models.BooleanField(_("first-party marketing consent"), default=False)
    partner_consent = models.BooleanField(_("third-party marketing consent"), default=False)
