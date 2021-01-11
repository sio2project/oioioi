import six
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class GlobalMessage(models.Model):
    message = models.TextField(verbose_name=_("message"))
    enabled = models.BooleanField(default=False, verbose_name=_("enabled"))
    start = models.DateTimeField(null=True, blank=True, verbose_name=_("start"))
    end = models.DateTimeField(null=True, blank=True, verbose_name=_("end"))

    def visible(self, timestamp):
        return (
            self.enabled
            and ((not self.start) or self.start <= timestamp)
            and ((not self.end) or timestamp <= self.end)
        )

    @staticmethod
    def get_singleton():
        msg, _ = GlobalMessage.objects.get_or_create(pk=1)
        return msg

    def __str__(self):
        return six.text_type(self.message)
