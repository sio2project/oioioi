# coding: utf-8
from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import PhoneNumberField, PostalCodeField
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.participants.models import RegistrationModel


check_django_app_dependencies(__name__, ['oioioi.participants'])

T_SHIRT_SIZES = [(s, s) for s in ('S', 'M', 'L', 'XL', 'XXL')]

JOB_TYPES = [
    ('PS', "Szkoła podstawowa"),
    ('MS', "Gimnazjum"),
    ('HS', "Szkoła ponadgimnazjalna"),
    ('OTH', "Inne"),
    ('AS', "Szkoła wyższa - student"),
    ('AD', "Szkoła wyższa - doktorant"),
    ('COM', "Firma"),
]


class PARegistration(RegistrationModel):
    job = models.CharField(max_length=7, choices=JOB_TYPES,
        verbose_name=_("job or school kind"))
    job_name = models.CharField(max_length=255,
        verbose_name=_("job or school name"))
    address = models.CharField(max_length=255, verbose_name=_("address"))
    postal_code = PostalCodeField(verbose_name=_("postal code"))
    city = models.CharField(max_length=100, verbose_name=_("city"))
    t_shirt_size = models.CharField(max_length=7, choices=T_SHIRT_SIZES,
        verbose_name=_("t-shirt size"))
    newsletter = models.BooleanField(_("newsletter"), help_text=_("I want to "
        "recieve the information about further editions of the contest."))
    terms_accepted = models.BooleanField(_("terms accepted"),
        help_text=_("I declare that I have read the contest rules and "
                    "the technical arrangements. I fully understand them and "
                     "accept them unconditionally."))
