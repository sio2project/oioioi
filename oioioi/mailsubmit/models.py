import os.path

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import Contest, ProblemInstance, Submission
from oioioi.filetracker.fields import FileField

check_django_app_dependencies(__name__, ['oioioi.contests', 'oioioi.programs'])


def make_submission_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'mailsubmissions/%s/%d%s' % (
        instance.problem_instance.contest_id,
        instance.id,
        os.path.splitext(filename)[1],
    )


class MailSubmission(models.Model):
    problem_instance = models.ForeignKey(
        ProblemInstance, verbose_name=_("problem"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, blank=True, null=True, verbose_name=_("user"), on_delete=models.CASCADE
    )
    date = models.DateTimeField(
        default=timezone.now, blank=True, verbose_name=_("date"), db_index=True
    )
    source_file = FileField(upload_to=make_submission_filename)
    submission = models.ForeignKey(
        Submission,
        blank=True,
        null=True,
        verbose_name=_("related submission"),
        on_delete=models.CASCADE,
    )
    accepted_by = models.ForeignKey(
        User,
        blank=True,
        null=True,
        verbose_name=_("accepted by"),
        related_name='+',
        on_delete=models.SET_NULL,
    )


@date_registry.register(
    'start_date', name_generator=(lambda obj: _("Mail submissions start")), order=0
)
@date_registry.register(
    'end_date', name_generator=(lambda obj: _("Mail submissions end")), order=0
)
class MailSubmissionConfig(models.Model):
    contest = models.OneToOneField(
        Contest, related_name='mail_submission_config', on_delete=models.CASCADE
    )
    enabled = models.BooleanField(verbose_name=_("enabled"), default=False)
    start_date = models.DateTimeField(verbose_name=_("start date"))
    end_date = models.DateTimeField(blank=True, null=True, verbose_name=_("end date"))
    printout_text = models.TextField(
        verbose_name=_("printout text"),
        help_text=_(
            "LaTeX-formatted text to show on the printed document "
            "sent by regular post; usually contains the instruction on "
            "how, where and when to send it."
        ),
        default=_(
            "This document confirms that you have uploaded a file "
            "for postal submission on our server. To have this file "
            "judged, send this document by mail to us."
        ),
    )

    class Meta(object):
        verbose_name = _("postal submission configuration")
        verbose_name_plural = _("postal submission configurations")
