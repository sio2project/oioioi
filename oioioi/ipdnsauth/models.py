from django.contrib.auth.models import User
from django.db import models

from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies

check_django_app_dependencies(__name__, ['oioioi.contestexcl'])


class IpToUser(models.Model):
    """Represents mapping for automatic authorization based on IP address."""

    ip_addr = models.GenericIPAddressField(
        unique=True, unpack_ipv4=True, verbose_name=_("IP address")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta(object):
        verbose_name = _("IP autoauth mapping")
        verbose_name_plural = _("IP autoauth mappings")

    def __str__(self):
        return str(self.ip_addr)


class DnsToUser(models.Model):
    """Represents mapping for automatic authorization based on DNS hostname."""

    dns_name = models.CharField(
        unique=True, max_length=255, verbose_name=_("DNS hostname")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta(object):
        verbose_name = _("DNS autoauth mapping")
        verbose_name_plural = _("DNS autoauth mappings")

    def __str__(self):
        return str(self.dns_name)
