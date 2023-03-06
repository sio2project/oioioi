# coding: utf-8
from importlib import import_module

import django.dispatch
from django.conf import settings

# pylint: disable=unused-import
# Important. This import is to register signal handlers. Do not remove it.
import oioioi.base.signal_handlers
from oioioi.base.captcha_check import captcha_check
from oioioi.base.setup_check import setup_check

# Check if deployment and installation config versions match.
# Check if database settings are correct.
setup_check()
captcha_check()

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            # Controllers should be imported at startup, because they register
            # mixins
            import_module(app + '.controllers')
        except ImportError:
            pass

import logging

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

auditLogger = logging.getLogger(__name__ + ".audit")

# Sender will be equal to the form that was completed
PreferencesSaved = django.dispatch.Signal()


class Consents(models.Model):
    user = models.OneToOneField(
        User, primary_key=True, verbose_name=_("user"), on_delete=models.CASCADE
    )
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)
    marketing_consent = models.BooleanField(
        _("first-party marketing consent"), default=False
    )
    partner_consent = models.BooleanField(
        _("third-party marketing consent"), default=False
    )


class UserPreferences(models.Model):
    user = models.OneToOneField(
        User, primary_key=True, verbose_name=_("user"), on_delete=models.CASCADE
    )

    language = models.CharField(
        _("preferred_language"),
        max_length=2,
        choices=list(settings.LANGUAGES) + [("", _("None"))],
        default=""
    )

    enable_editor = models.BooleanField(
        _("enable_editor"),
        default=False,
    )


@receiver(post_save, sender=Consents)
def _log_consent_change(sender, instance, created, raw, **kwargs):
    auditLogger.info(
        "User %d (%s) consents changed: terms: %s marketing: %s partner: %s",
        instance.user.id,
        instance.user.username,
        instance.terms_accepted,
        instance.marketing_consent,
        instance.partner_consent,
    )
