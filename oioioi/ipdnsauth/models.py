from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class IpToUser(models.Model):
    """Represents mapping for automatic authorization based on IP address."""
    ip_addr = models.GenericIPAddressField(unique=True, unpack_ipv4=True,
                                           verbose_name=_("IP address"))
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = _("IP autoauth mapping")
        verbose_name_plural = _("IP autoauth mappings")

    def __unicode__(self):
        return self.ip_addr

class DnsToUser(models.Model):
    """Represents mapping for automatic authorization based on DNS hostname."""
    dns_name = models.CharField(unique=True, max_length=255,
                                 verbose_name=_("DNS hostname"))
    user = models.ForeignKey(User)

    class Meta:
        verbose_name = _("DNS autoauth mapping")
        verbose_name_plural = _("DNS autoauth mappings")

    def __unicode__(self):
        return self.dns_name
