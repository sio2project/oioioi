from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Round, Contest


class QuizQuestion(models.Model):
    text = models.TextField(_("question"))

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("questions")

    def __unicode__(self):
        return unicode(self.text)


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='answers')
    text = models.TextField(_("answer"))
    is_correct = models.BooleanField(_("is correct"), default=False)

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("answers")

    def __unicode__(self):
        return unicode(self.text)


class QuizInstance(models.Model):
    contest = models.OneToOneField(Contest, on_delete=models.CASCADE)
    round = models.OneToOneField(Round, on_delete=models.CASCADE)
    questions = models.IntegerField(_("number of questions"), default=10)
    attempts = models.IntegerField(_("number of attempts"), default=2)
    time = models.IntegerField(_("available time in minutes"), default=30)
    max_points = models.IntegerField(_("max number of points to gain"), default=100)
    start_date = models.DateTimeField(default=timezone.now, verbose_name=_("start date"))
    end_date = models.DateTimeField(default=timezone.now, verbose_name=_("end date"))

    class Meta:
        verbose_name = _("quiz")
        verbose_name_plural = _("quizes")

    def __unicode__(self):
        return unicode("{} {} {}".format(_("Quiz"), _("inside"), self.round))

    def is_open(self):
        return self.start_date <= timezone.now() < self.end_date


class QuizSubmission(models.Model):
    quiz = models.ForeignKey(QuizInstance, on_delete=models.CASCADE, related_name='submissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now, verbose_name=_("start date"))
    end_date = models.DateTimeField(default=None, verbose_name=_("end date"), null=True)
    score = models.IntegerField(_("score"), default=0)

    class Meta:
        verbose_name = _("submission")
        verbose_name_plural = _("submissions")

    def __unicode__(self):
        return unicode("{} {}".format(_("submission of"), self.user))


class QuizUserAnswer(models.Model):
    submission = models.ForeignKey(
        QuizSubmission,
        on_delete=models.CASCADE,
        related_name='user_answers',
        verbose_name=_('submission'))
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        verbose_name=_('question'))
    answer = models.ForeignKey(
        QuizAnswer,
        on_delete=models.CASCADE,
        verbose_name=_('answer'),
        null=True)

    def is_correct(self):
        return self.answer.is_correct

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("answers")

    def __unicode__(self):
        return unicode(self.submission)
