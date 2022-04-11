import six
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from django.utils.translation import gettext_lazy as _

from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.base.utils.validators import validate_db_string_id
from oioioi.contests.models import Contest
from oioioi.participants.fields import OneToOneBothHandsCascadingParticipantField

check_django_app_dependencies(__name__, ['oioioi.contestexcl'])


participant_statuses = EnumRegistry()
participant_statuses.register('ACTIVE', _("Active"))
participant_statuses.register('BANNED', _("Banned"))
participant_statuses.register('DELETED', _("Account deleted"))



class Participant(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = EnumField(participant_statuses, default='ACTIVE')
    anonymous = models.BooleanField(default=False)

    @property
    def registration_model(self):
        rcontroller = self.contest.controller.registration_controller()
        model_class = rcontroller.get_model_class()

        if model_class is None:
            raise ObjectDoesNotExist

        try:
            return model_class.objects.get(participant=self)
        except model_class.DoesNotExist:
            raise ObjectDoesNotExist

    class Meta(object):
        unique_together = ('contest', 'user')

    def __str__(self):
        return six.text_type(self.user)

    def erase_data(self):
        """Replaces (and saves) values of every field to values suggesting
        that the account is deleted. Purpose: delete user's private data
        from the system.

        Used only when account is being deleted by user.
        """
        try:
            self.registration_model.erase_data()
        except ObjectDoesNotExist:
            pass

        self.status = 'DELETED'
        self.anonymous = True
        self.save()



class Region(models.Model):
    short_name = models.CharField(max_length=10, validators=[validate_db_string_id])
    name = models.CharField(max_length=255)
    contest = models.ForeignKey(
        Contest, related_name='regions', on_delete=models.CASCADE
    )
    region_server = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Region server"),
        help_text=_("IP address or hostname of the regional server"),
    )

    class Meta(object):
        unique_together = ('contest', 'short_name')

    def __str__(self):
        return u'%s' % (self.short_name,)


class RegistrationModel(models.Model):
    participant = OneToOneBothHandsCascadingParticipantField(
        Participant, related_name='%(app_label)s_%(class)s', on_delete=models.CASCADE
    )

    class Meta(object):
        abstract = True

    def erase_data(self):
        pass


class OpenRegistration(RegistrationModel):
    terms_accepted = models.BooleanField(
        _("terms accepted"),
        help_text=_(
            "I declare that I have read the contest rules and "
            "the technical arrangements. I fully understand them and "
            "accept them unconditionally."
        ),
        default=False,
    )

    def erase_data(self):
        self.terms_accepted = False
        self.save()



class OnsiteRegistration(RegistrationModel):
    number = models.IntegerField(verbose_name=_("number"))
    region = models.ForeignKey(
        Region, null=True, on_delete=models.SET_NULL, verbose_name=_("region")
    )
    local_number = models.IntegerField(verbose_name=_("local number"))

    class Meta(object):
        unique_together = ('region', 'local_number')

    def __str__(self):
        return _("%(number)s/%(region)s/%(local_number)s") % {
            'number': self.number,
            'region': self.region,
            'local_number': self.local_number,
        }

    def erase_data(self):
        self.number = -1
        self.region = None
        self.local_number = -1
        self.save()


class TestRegistration(RegistrationModel):
    __test__ = False
    """Used only for testing"""
    name = models.CharField(max_length=255)


class TermsAcceptedPhrase(models.Model):
    """This model stores text asking user to accept contest's terms.

    It is used in contests with custom registration: PA and OI.
    """

    text = models.TextField(_("text"), null=True, max_length=500)
    contest = models.OneToOneField(
        Contest, related_name='terms_accepted_phrase', on_delete=models.CASCADE
    )

    # Verbose names in Meta could be a little misleading.
    # This is because they are not 100% accurate, but look nice in admin view.
    class Meta(object):
        # In StackedInline verbose_name_plural is used as a header of inline.
        verbose_name_plural = _("text asking participant to accept contest terms")
        verbose_name = _("text asking participant to accept contest terms")

    # This is used as a name of the given object displayed in TabularInline.
    # We are using it to display only one object of type TermsAcceptedPhrase so
    # it is not necessary to name it.
    def __str__(self):
        return u""
