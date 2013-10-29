from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from oioioi.contests.models import ProblemInstance, Contest
from oioioi.base.utils.color import ColorField
from oioioi.base.utils.deps import check_django_app_dependencies


check_django_app_dependencies(__name__, ['oioioi.participants'])


class ProblemBalloonsConfig(models.Model):
    problem_instance = models.OneToOneField(ProblemInstance,
                                   verbose_name=_("problem"),
                                   related_name='balloons_config',
                                   primary_key=True)
    color = ColorField(verbose_name=_("color"))

    class Meta(object):
        verbose_name = _("balloons colors")
        verbose_name_plural = _("balloons colors")

    def __unicode__(self):
        return unicode(self.problem_instance) + ' (' + self.color + ')'


class BalloonsDisplay(models.Model):
    """Represents mapping for balloons display."""
    ip_addr = models.GenericIPAddressField(unique=True, unpack_ipv4=True,
                                           verbose_name=_("IP address"))
    user = models.ForeignKey(User, verbose_name=_("user"))
    contest = models.ForeignKey(Contest, verbose_name=_("contest"))

    class Meta(object):
        verbose_name = _("balloons display")
        verbose_name_plural = _("balloons displays")

    def __unicode__(self):
        return self.ip_addr
