from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Submission

check_django_app_dependencies(__name__, ['oioioi.oi'])


class OISubmitExtraData(models.Model):
    submission = models.OneToOneField(Submission)
    localtime = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("local time"))
    siotime = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("sio time"))
    servertime = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("server time"))
    received_suspected = models.BooleanField(default=False,
                                    verbose_name=_("received suspected"))
    comments = models.CharField(max_length=255)
