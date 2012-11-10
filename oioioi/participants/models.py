from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.base.fields import EnumRegistry, EnumField
from oioioi.contests.models import Contest

participant_statuses = EnumRegistry()
participant_statuses.register('ACTIVE', _("Active"))
participant_statuses.register('BANNED', _("Banned"))

class Participant(models.Model):
    contest = models.ForeignKey(Contest)
    user = models.ForeignKey(User)
    status = EnumField(participant_statuses, default='ACTIVE')

    class Meta:
        unique_together = ('contest', 'user')

    def __unicode__(self):
        return unicode(self.user)

class RegistrationModel(models.Model):
    participant = models.OneToOneField(Participant,
            related_name='%(app_label)s_%(class)s')

    class Meta:
        abstract = True
