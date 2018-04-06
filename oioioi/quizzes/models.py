from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import EnumField
from oioioi.contests.fields import ScoreField
from oioioi.contests.models import Submission, SubmissionReport, \
    submission_statuses
from oioioi.problems.models import Problem


class Quiz(Problem):

    class Meta(object):
        verbose_name = _("quiz")
        verbose_name_plural = _("quizzes")


class QuizQuestion(models.Model):
    question = models.TextField(verbose_name=_("question"))
    is_multiple_choice = models.BooleanField(default=False, verbose_name=_(
        "is multiple choice"))
    points = models.IntegerField(default=1, verbose_name=_("points"))
    quiz = models.ForeignKey(Quiz, verbose_name=_("quiz"))
    order = models.IntegerField(default=0, verbose_name=_("order"))

    class Meta(object):
        ordering = ['order']
        verbose_name = _("quiz question")
        verbose_name_plural = _("quiz questions")


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, verbose_name=_("question"))
    answer = models.TextField(verbose_name=_("answer"))
    is_correct = models.BooleanField(default=False,
                                     verbose_name=_("is answer correct"))
    order = models.IntegerField(default=0, verbose_name=_("order"))

    class Meta(object):
        ordering = ['order']
        verbose_name = _("quiz answer")
        verbose_name_plural = _("quiz answers")


class QuizSubmission(Submission):

    class Meta(object):
        verbose_name = _("quiz submission")
        verbose_name_plural = _("quiz submissions")


class QuizSubmissionAnswer(models.Model):
    quiz_submission = models.ForeignKey(QuizSubmission,
                                        verbose_name=_("quiz submission"))
    answer = models.ForeignKey(QuizAnswer, verbose_name=_("answer"),
                               on_delete=models.SET_NULL, null=True)
    is_selected = models.BooleanField(default=False,
                                      verbose_name=_("is anwser selected"))

    class Meta(object):
        verbose_name = _("quiz submission answer")
        verbose_name_plural = _("quiz submission answers")


class QuestionReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport,
                                        verbose_name=_("submission report"))
    comment = models.TextField(blank=True, null=True,
                                    verbose_name=_("comment"))
    score = ScoreField(verbose_name=_("score"))
    question = models.ForeignKey(QuizQuestion, blank=True, null=True,
                             on_delete=models.SET_NULL, verbose_name=_("question"))
    question_max_score = models.IntegerField(verbose_name=_("question max score"))
    status = EnumField(submission_statuses, default='WA', verbose_name=_("status"))

    class Meta(object):
        verbose_name = _("question report")
        verbose_name_plural = _("question reports")
