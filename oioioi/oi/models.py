# coding: utf-8
import difflib
import urllib

import urllib.parse
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.base.utils.validators import validate_whitespaces
from oioioi.contests.models import Contest
from oioioi.participants.models import RegistrationModel

check_django_app_dependencies(__name__, ['oioioi.participants'])

T_SHIRT_SIZES = [(s, s) for s in ('S', 'M', 'L', 'XL', 'XXL')]

PROVINCES = [
    (s, s)
    for s in (
        u'dolnośląskie',
        u'kujawsko-pomorskie',
        u'lubelskie',
        u'lubuskie',
        u'łódzkie',
        u'małopolskie',
        u'mazowieckie',
        u'opolskie',
        u'podkarpackie',
        u'podlaskie',
        u'pomorskie',
        u'śląskie',
        u'świętokrzyskie',
        u'warmińsko-mazurskie',
        u'wielkopolskie',
        u'zachodniopomorskie',
        u'zagranica',
    )
]

CLASS_TYPES = [
    ('1LO', "pierwsza szkoły średniej"),
    ('2LO', "druga szkoły średniej"),
    ('3LO', "trzecia szkoły średniej"),
    ('4LO', "czwarta szkoły średniej"),
    ('5LO', "piąta szkoły średniej"),
    ('1G', "pierwsza gimnazjum"),
    ('2G', "druga gimnazjum"),
    ('3G', "trzecia gimnazjum"),
    ('1SP', "pierwsza szkoły podstawowej"),
    ('2SP', "druga szkoły podstawowej"),
    ('3SP', "trzecia szkoły podstawowej"),
    ('4SP', "czwarta szkoły podstawowej"),
    ('5SP', "piąta szkoły podstawowej"),
    ('6SP', "szósta szkoły podstawowej"),
    ('7SP', "siódma szkoły podstawowej"),
    ('8SP', "ósma szkoły podstawowej"),
]


class SchoolType(models.Model):
    name = models.CharField(
        max_length=255, validators=[validate_whitespaces], verbose_name=_("name")
    )


class School(models.Model):
    rspo = models.PositiveIntegerField(blank=True, null=True, unique=True)
    type = models.ForeignKey(SchoolType, null=True, on_delete=models.SET_NULL)
    name = models.CharField(
        max_length=255, validators=[validate_whitespaces], verbose_name=_("name")
    )
    address = models.CharField(max_length=255, verbose_name=_("address"))
    postal_code = models.CharField(
        max_length=6,
        verbose_name=_("postal code"),
        db_index=True,
        validators=[
            RegexValidator(
                r'^\d{2}-\d{3}$', _("Enter a postal code in the format XX-XXX")
            )
        ],
    )
    city = models.CharField(max_length=100, verbose_name=_("city"), db_index=True)
    province = models.CharField(
        max_length=100, choices=PROVINCES, verbose_name=_("province"), db_index=True
    )
    phone = models.CharField(
        max_length=64,
        validators=[RegexValidator(r'\+?[0-9() -]{6,}', _("Invalid phone number"))],
        verbose_name=_("phone number"),
        null=True,
        blank=True,
    )
    email = models.EmailField(blank=True, verbose_name=_("email"))

    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    is_approved = models.BooleanField(default=True, verbose_name=_("approved"))

    class Meta(object):
        unique_together = ('name', 'postal_code')
        indexes = [models.Index(fields=("city", "is_active")), models.Index(fields=("province", "is_active"))]
        ordering = ['province', 'city', 'address', 'name']

    def __str__(self):
        return _("%(name)s, %(city)s") % {'name': self.name, 'city': self.city}

    def get_participants_url(self):
        url = reverse('oioioiadmin:participants_participant_changelist')
        query = (self.postal_code + ' ' + self.name).encode('utf8')
        return url + '?' + urllib.parse.urlencode({'q': query})

    def is_similar(self, instance):
        ratio = difflib.SequenceMatcher(
            None, self.address.lower(), instance.address.lower()
        ).ratio()
        return ratio > 0.75



class OIRegistration(RegistrationModel):
    address = models.CharField(max_length=255, verbose_name=_("address"))
    postal_code = models.CharField(
        max_length=6,
        verbose_name=_("postal code"),
        validators=[
            RegexValidator(
                r'^\d{2}-\d{3}$', _("Enter a postal code in the format XX-XXX")
            )
        ],
    )
    city = models.CharField(max_length=100, verbose_name=_("city"))
    phone = models.CharField(
        max_length=64,
        validators=[RegexValidator(r'\+?[0-9() -]{6,}', _("Invalid phone number"))],
        verbose_name=_("phone number"),
        null=True,
        blank=True,
    )
    birthday = models.DateField(verbose_name=_("birth date"))
    birthplace = models.CharField(max_length=255, verbose_name=_("birthplace"))
    t_shirt_size = models.CharField(
        max_length=7, choices=T_SHIRT_SIZES, verbose_name=_("t-shirt size")
    )
    school = models.ForeignKey(
        School, null=True, verbose_name=_("school"), on_delete=models.CASCADE
    )
    class_type = models.CharField(
        max_length=7, choices=CLASS_TYPES, verbose_name=_("class")
    )
    # It is presented with the default verbose name in all contexts, except for
    # the custom registration form (in contests like OI and PA)
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)

    def __str__(self):
        return _("%(class_type)s of %(school)s") % {
            'class_type': self.get_class_type_display(),
            'school': self.school,
        }

    def erase_data(self):
        self.address = 'Account deleted'
        self.postal_code = '00-000'
        self.city = 'Account deleted'
        self.phone = None
        self.birthday = '1900-01-01'
        self.birthplace = 'Account deleted'
        self.t_shirt_size = 'S'
        self.school = None
        self.class_type = 'None'
        self.terms_accepted = False
        self.save()
