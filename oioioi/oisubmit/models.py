from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Submission

class OISubmitExtraData(models.Model):
    submission = models.OneToOneField(Submission)
    localtime = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("local time"))
    siotime = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("sio time"))
    servertime = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("server time"))
    is_suspected = models.BooleanField(default=False,
                                    verbose_name=_("is suspected"))
    comments = models.CharField(max_length=255)
