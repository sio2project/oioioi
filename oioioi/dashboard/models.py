from django.utils.translation import gettext_lazy as _

from oioioi.base.models import PublicMessage


class DashboardMessage(PublicMessage):
    class Meta(object):
        verbose_name = _("dashboard message")
        verbose_name_plural = _("dashboard messages")
