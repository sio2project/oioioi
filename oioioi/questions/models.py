import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.base.utils.validators import validate_whitespaces
from oioioi.contests.models import Contest, ProblemInstance, Round

message_kinds = EnumRegistry()
message_kinds.register('QUESTION', _("Question"))
message_kinds.register('PRIVATE', _("Private message"))
message_kinds.register('PUBLIC', _("Public message"))

message_kind_labels = EnumRegistry()
message_kind_labels.register('QUESTION', _("QUESTION"))
message_kind_labels.register('PRIVATE', _("PRIVATE"))
message_kind_labels.register('PUBLIC', _("PUBLIC"))

logger = logging.getLogger('oioioi')



class Message(models.Model):
    contest = models.ForeignKey(
        Contest, null=True, blank=True, on_delete=models.CASCADE
    )
    round = models.ForeignKey(Round, null=True, blank=True, on_delete=models.CASCADE)
    problem_instance = models.ForeignKey(
        ProblemInstance, null=True, blank=True, on_delete=models.CASCADE
    )
    top_reference = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = EnumField(message_kinds, default='QUESTION', verbose_name=_("kind"))
    topic = models.CharField(
        max_length=255,
        verbose_name=_("topic"),
        validators=[MaxLengthValidator(255), validate_whitespaces],
    )
    content = models.TextField(verbose_name=_("content"))
    date = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name=_("date")
    )
    pub_date = models.DateTimeField(
        default=None, blank=True, null=True, verbose_name=_("publication date")
    )
    mail_sent = models.BooleanField(
        default=False, verbose_name=_("mail notification sent")
    )

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
            related = Message.objects.filter(
                Q(id=self.top_reference_id) | Q(top_reference_id=self.top_reference_id)
            )
        elif self.id:
            related = self.message_set.all()
        else:
            related = Message.objects.none()
        if self.id:
            related.exclude(id=self.id)
        related.update(
            round=self.round,
            contest=self.contest,
            problem_instance=self.problem_instance,
        )

        super(Message, self).save(*args, **kwargs)

    def can_have_replies(self):
        return self.kind == 'QUESTION'

    def _has_category(self):
        return self.round is not None or self.problem_instance is not None

    def __str__(self):
        return u'%s - %s' % (message_kinds.get(self.kind, self.kind), self.topic)

    @property
    def to_quote(self):
        lines = self.content.strip().split('\n')
        return ''.join('> ' + l for l in lines)

    def get_absolute_url(self):
        link = reverse(
            'message',
            kwargs={
                'contest_id': self.contest.id,
                'message_id': self.top_reference_id
                if self.top_reference_id is not None
                else self.id,
            },
        )
        return link

    def get_user_date(self):
        """ returns date visible by a user """
        return self.pub_date if self.pub_date is not None else self.date

    def get_kind_label(self):
        return message_kind_labels[self.kind]



class ReplyTemplate(models.Model):
    contest = models.ForeignKey(
        Contest, null=True, blank=True, on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, verbose_name=_("visible name"), blank=True)
    content = models.TextField(verbose_name=_("content"))
    # Incremented every time admin includes this template in a reply.
    usage_count = models.IntegerField(verbose_name=_("usage count"), default=0)

    def __str__(self):
        return u'%s: %s' % (self.visible_name, self.content)

    @property
    def visible_name(self):
        if self.name:
            return self.name
        length = getattr(settings, 'REPLY_TEMPLATE_VISIBLE_NAME_LENGTH', 15)
        return Truncator(self.content).chars(length)


class MessageView(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now, editable=False)

    class Meta(object):
        unique_together = ('message', 'user')


class MessageNotifierConfig(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, verbose_name=_("username"), on_delete=models.CASCADE)

    class Meta(object):
        unique_together = ('contest', 'user')
        verbose_name = _("notified about new questions")
        verbose_name_plural = _("notified about new questions")


@receiver(post_save, sender=Message)
def send_notification(sender, instance, created, **kwargs):
    # Don't send a notification when the message was just edited
    if not created:
        return

    # Send a notification if this is a new public message
    if instance.kind == 'PUBLIC' and instance.contest is not None:
        if instance.problem_instance is not None:
            logger.info(
                "Public message \"%(topic)s\""
                " about problem \"%(short_name)s\" was created",
                {
                    'topic': instance.topic,
                    'short_name': instance.problem_instance.short_name,
                },
                extra={
                    'notification': 'new_public_message',
                    'message_instance': instance,
                    'contest': instance.contest,
                },
            )
        else:
            logger.info(
                "Public message \"%(topic)s\" was created",
                {'topic': instance.topic},
                extra={
                    'notification': 'new_public_message',
                    'message_instance': instance,
                    'contest': instance.contest,
                },
            )

    # Send a notification if this is a new answer for question
    elif instance.top_reference is not None:
        if instance.problem_instance is not None:
            logger.info(
                "Answer for question \"%(topic)s\""
                " about problem \"%(short_name)s\" was sent",
                {
                    'topic': instance.topic,
                    'short_name': instance.top_reference.problem_instance.short_name,
                },
                extra={
                    'notification': 'question_answered',
                    'question_instance': instance.top_reference,
                    'answer_instance': instance,
                    'user': instance.top_reference.author,
                },
            )

        else:
            logger.info(
                "Answer for question \"%(topic)s\" was sent",
                {'topic': instance.topic},
                extra={
                    'notification': 'question_answered',
                    'question_instance': instance.top_reference,
                    'answer_instance': instance,
                    'user': instance.top_reference.author,
                },
            )


# an e-mail notification will be spawned for every post
# with Message.top_reference == EmailSubscription.opening_post
class QuestionSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
