import os

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

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
    not_primaryschool = models.BooleanField(
        verbose_name="not primary school",
        default=False,
    )

    def erase_data(self):
        self.not_primaryschool = False
        self.save()
