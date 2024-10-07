import os

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.oi.models import CLASS_TYPES, School
from oioioi.participants.models import RegistrationModel

check_django_app_dependencies(__name__, ['oioioi.newsfeed', 'oioioi.teachers'])


def make_consent_filename(instance, filename):
    stem, ext = os.path.splitext(filename)
    return 'consents/%s/%s/%s' % (
        instance.participant.contest.id,
        instance.participant.user.id,
        'zgoda' + ext,
    )


def get_consent_url(instance):
    return reverse('view_consent', args=[instance.participant.id])


class MAPCourseRegistration(RegistrationModel):
    birthday = models.DateField(verbose_name=_("birth date"))
    school = models.ForeignKey(
        School, null=True, verbose_name=_("school"), on_delete=models.CASCADE
    )
    class_type = models.CharField(
        max_length=7, choices=CLASS_TYPES, verbose_name=_("class")
    )
    parent_consent = models.FileField(
        verbose_name="Zdjęcie/skan formularza zgody rodziców w przypadku bycia niepełnoletnim",
        upload_to=make_consent_filename,
    )
    parent_consent.file_url = get_consent_url

    def erase_data(self):
        self.birthday = '1900-01-01'
        self.class_type = 'None'
        self.parent_consent = ''
        self.save()
