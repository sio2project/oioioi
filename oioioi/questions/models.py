from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.base.fields import EnumRegistry, EnumField

message_kinds = EnumRegistry()
message_kinds.register('QUESTION', _("Question"))
message_kinds.register('PRIVATE', _("Private message"))
message_kinds.register('PUBLIC', _("Public message"))

class Message(models.Model):
    contest = models.ForeignKey(Contest, null=True, blank=True)
    round = models.ForeignKey(Round, null=True, blank=True)
    problem_instance = models.ForeignKey(ProblemInstance, null=True,
            blank=True)
    top_reference = models.ForeignKey('self', null=True, blank=True)
    author = models.ForeignKey(User)
    kind = EnumField(message_kinds, default='QUESTION')
    topic = models.CharField(max_length=255,
            validators=[MaxLengthValidator(255)])
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True, editable=False)

    def can_have_replies(self):
        return self.kind == 'QUESTION'

    def save(self):
        if self.top_reference:
            self.contest = self.top_reference.contest
            self.round = self.top_reference.round
            self.problem_instance = self.top_reference.problem_instance
        elif bool(self.round) == bool(self.problem_instance):
            raise ValueError(_("Exactly one of round or problem_instance must "
                               "be set"))
        if self.problem_instance:
            self.round = self.problem_instance.round
        self.contest = self.round.contest
        super(Message, self).save()

class MessageView(models.Model):
    message = models.ForeignKey(Message)
    user = models.ForeignKey(User)
    date = models.DateTimeField(auto_now_add=True, editable=False)
