from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.problems.models import Problem
from oioioi.base.fields import EnumRegistry, EnumField

message_kinds = EnumRegistry()
message_kinds.register('QUESTION', _("Question"))
message_kinds.register('PRIVATE', _("Private message"))
message_kinds.register('PUBLIC', _("Public message"))

class Message(models.Model):
    contest = models.ForeignKey(Contest, null=True, blank=True)
    problem_instance = models.ForeignKey(ProblemInstance, null=True,
            blank=True)
    problem = models.ForeignKey(Problem, null=True, blank=True)
    top_reference = models.ForeignKey('self', null=True, blank=True)
    author = models.ForeignKey(User)
    kind = EnumField(message_kinds, default='QUESTION')
    topic = models.CharField(max_length=255)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True, editable=False)

    def save(self):
        if self.top_reference:
            self.contest = self.top_reference.contest
            self.problem_instance = self.top_reference.problem_instance
            self.problem = self.top_reference.problem
        if bool(self.contest) == bool(self.problem):
            raise ValueError("Exactly one of contest or problem must "
                "be set")
        if self.problem_instance:
            self.contest = self.problem_instance.contest
        super(Message, self).save()

class MessageView(models.Model):
    message = models.ForeignKey(Message)
    user = models.ForeignKey(User)
    date = models.DateTimeField(auto_now_add=True, editable=False)
