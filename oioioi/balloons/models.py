import six
from django.contrib.auth.models import User
from django.db import models

from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils import generate_key
from oioioi.base.utils.color import ColorField
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Contest, ProblemInstance

check_django_app_dependencies(__name__, ['oioioi.participants', 'oioioi.acm'])



class ProblemBalloonsConfig(models.Model):
    problem_instance = models.OneToOneField(
        ProblemInstance,
        verbose_name=_("problem"),
        related_name='balloons_config',
        primary_key=True,
        on_delete=models.CASCADE,
    )
    color = ColorField(verbose_name=_("color"))

    class Meta(object):
        verbose_name = _("balloons colors")
        verbose_name_plural = _("balloons colors")

    def __str__(self):
        return (
            six.text_type(self.problem_instance)
            + u' ('
            + six.text_type(self.color)
            + u')'
        )



class BalloonsDisplay(models.Model):
    """Represents mapping for balloons display."""

    ip_addr = models.GenericIPAddressField(
        unique=True, unpack_ipv4=True, verbose_name=_("IP address")
    )
    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.CASCADE)
    contest = models.ForeignKey(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )

    class Meta(object):
        verbose_name = _("balloons display")
        verbose_name_plural = _("balloons displays")

    def __str__(self):
        return six.text_type(self.ip_addr)



class BalloonDelivery(models.Model):
    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.CASCADE)
    problem_instance = models.ForeignKey(
        ProblemInstance, verbose_name=_("problem"), on_delete=models.CASCADE
    )
    delivered = models.BooleanField(default=False, verbose_name=_("delivered"))
    first_accepted_solution = models.BooleanField(
        default=False, verbose_name=_("first accepted solution")
    )

    class Meta(object):
        verbose_name = _("balloon delivery")
        verbose_name_plural = _("balloon deliveries")
        unique_together = ('user', 'problem_instance')
        ordering = ['id']

    def __str__(self):
        return u'%(user)s for %(problem)s (%(delivered)s)' % {
            u'user': self.user,
            u'problem': self.problem_instance,
            u'delivered': u'delivered' if self.delivered else u'not delivered',
        }


class BalloonsDeliveryAccessData(models.Model):
    contest = models.OneToOneField(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    access_key = models.CharField(max_length=16, verbose_name=_("access key"))
    valid_until = models.DateTimeField(null=True, verbose_name=_("valid until"))

    class Meta(object):
        verbose_name = _("balloons delivery access data")
        verbose_name_plural = _("balloons delivery access data")

    def generate_key(self):
        self.access_key = generate_key()[:16]
