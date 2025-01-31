from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class WelcomePageMessage(models.Model):
    content = models.TextField(verbose_name=_("message"), blank=True)
    language = models.CharField(max_length=6, verbose_name=_("language code"))

    class Meta:
        verbose_name = _("welcome page message")
        verbose_name_plural = _("welcome page messages")

    def render_content(self):
        return mark_safe(self.content)
