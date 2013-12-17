from django.db import models
from django.db.models import Q
from django.dispatch import receiver, Signal
from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.base.fields import EnumRegistry, EnumField
from oioioi.base.utils.validators import validate_whitespaces
from oioioi.questions.utils import send_email_about_new_question

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
    kind = EnumField(message_kinds, default='QUESTION', verbose_name=_("kind"))
    topic = models.CharField(max_length=255, verbose_name=_("topic"),
            validators=[MaxLengthValidator(255), validate_whitespaces])
    content = models.TextField(verbose_name=_("content"))
    date = models.DateTimeField(default=timezone.now, editable=False,
            verbose_name=_("date"))

    def save(self, *args, **kwargs):
        # Assert integrity in this Message
        if not self._has_category():
            assert self.top_reference and self.top_reference._has_category()
            self.problem_instance = self.top_reference.problem_instance
            self.round = self.top_reference.round
        elif self.problem_instance:
            self.round = self.problem_instance.round
        self.contest = self.round.contest

        # Propagate to all related Messages
        if self.top_reference:
            related = Message.objects.filter(Q(id=self.top_reference_id) |
                      Q(top_reference_id=self.top_reference_id))
        else:
            related = self.message_set.all()
        if self.id:
            related.exclude(id=self.id)
        related.update(round=self.round, contest=self.contest,
                       problem_instance=self.problem_instance)

        super(Message, self).save(*args, **kwargs)

    def can_have_replies(self):
        return self.kind == 'QUESTION'

    def _has_category(self):
        return self.round is not None or self.problem_instance is not None

    def __unicode__(self):
        return u'%s - %s' % (message_kinds.get(self.kind, self.kind),
                             self.topic)

    @property
    def to_quote(self):
        lines = self.content.strip().split('\n')
        return ''.join('> ' + l for l in lines)


class ReplyTemplate(models.Model):
    contest = models.ForeignKey(Contest, null=True, blank=True)
    name = models.CharField(max_length=255, verbose_name=_("visible name"),
                            blank=True)
    content = models.TextField(verbose_name=_("content"))
    # Incremented every time admin includes this template in a reply.
    usage_count = models.IntegerField(verbose_name=_("usage count"), default=0)

    def __unicode__(self):
        return u'%s: %s' % (self.visible_name, self.content)

    @property
    def visible_name(self):
        if self.name:
            return self.name
        length = getattr(settings, 'REPLY_TEMPLATE_VISIBLE_NAME_LENGTH', 15)
        return Truncator(self.content).chars(length)


class MessageView(models.Model):
    message = models.ForeignKey(Message)
    user = models.ForeignKey(User)
    date = models.DateTimeField(default=timezone.now, editable=False)

    class Meta(object):
        unique_together = ('message', 'user')


class MessageNotifierConfig(models.Model):
    contest = models.ForeignKey(Contest)
    user = models.ForeignKey(User, verbose_name=_("username"))

    class Meta(object):
        unique_together = ('contest', 'user')
        verbose_name = _("notified about new questions")
        verbose_name_plural = _("notified about new questions")


new_question_signal = Signal(providing_args=['request', 'instance'])


@receiver(new_question_signal)
def notify_about_new_question(sender, request, instance, **kwargs):
    conf = MessageNotifierConfig.objects.filter(contest=instance.contest)
    users_to_notify = [x.user for x in conf]
    for u in users_to_notify:
        send_email_about_new_question(u, request, instance)
