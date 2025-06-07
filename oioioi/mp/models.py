# coding: utf-8
from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies

from oioioi.participants.models import RegistrationModel
from oioioi.contests.models import Contest
from oioioi.oi.models import School

check_django_app_dependencies(__name__, ['oioioi.contests'])


class MPRegistration(RegistrationModel):
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)

    def erase_data(self):
        self.terms_accepted = False
        self.save()


class MP2025Registration(RegistrationModel):
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)
    birth_year = models.IntegerField(_("year of birth"))
    city = models.CharField(max_length=100, verbose_name=_("city"))
    school = models.ForeignKey(
        School,
        null=True,
        verbose_name=_("school"),
        on_delete=models.CASCADE,
        blank=True,
    )
    teacher = models.CharField(
        max_length=100, verbose_name=_("teacher's name"), blank=True
    )

    def erase_data(self):
        self.terms_accepted = False
        self.birth_year = 1900
        self.city = 'Account deleted'
        self.school = None
        self.teacher = 'Account deleted'
        self.save()


class SubmissionScoreMultiplier(models.Model):
    """If SubmissionScoreMultiplier exists, users can submit problems
    even after round ends, until end_date

    Result score for submission after round's end is multiplied by
    given multiplier value
    """

    contest = models.OneToOneField(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    multiplier = models.FloatField(_("multiplier"))
    end_date = models.DateTimeField(_("end date"))
