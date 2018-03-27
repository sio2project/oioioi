from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import EnumField
from oioioi.contests.fields import ScoreField
from oioioi.contests.models import Submission, SubmissionReport, \
    submission_statuses
from oioioi.problems.models import Problem


class Quiz(Problem):

    class Meta(object):
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")


class QuizQuestion(models.Model):
    question = models.TextField(verbose_name=_("Question"))
    is_multiple_choice = models.BooleanField(default=False, verbose_name=_(
        "Is multiple choice"))
    points = models.IntegerField(default=1, verbose_name=_("Points"))
    quiz = models.ForeignKey(Quiz, verbose_name=_("Quiz"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))

    class Meta(object):
        ordering = ['order']
        verbose_name = _("Quiz question")
        verbose_name_plural = _("Quiz questions")


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, verbose_name=_("Question"))
    answer = models.TextField(verbose_name=_("Answer"))
    is_correct = models.BooleanField(default=False,
                                     verbose_name=_("Is answer correct"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))

    class Meta(object):
        ordering = ['order']
        verbose_name = _("Quiz answer")
        verbose_name_plural = _("Quiz answers")


class QuizSubmission(Submission):

    class Meta(object):
        verbose_name = _("Quiz submission")
        verbose_name_plural = _("Quiz submissions")


class QuizSubmissionAnswer(models.Model):
    quiz_submission = models.ForeignKey(QuizSubmission,
                                        verbose_name=_("Quiz submission"))
    answer = models.ForeignKey(QuizAnswer, verbose_name=_("Answer"),
                               on_delete=models.SET_NULL, null=True)
    is_selected = models.BooleanField(default=False,
                                      verbose_name=_("Is answer selected"))

    class Meta(object):
        verbose_name = _("Quiz submission answer")
        verbose_name_plural = _("Quiz submission answers")


class QuestionReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport,
                                        verbose_name=_("Submission report"))
    comment = models.TextField(blank=True, null=True,
                                    verbose_name=_("Comment"))
    score = ScoreField(verbose_name=_("Score"))
    question = models.ForeignKey(QuizQuestion, blank=True, null=True,
                             on_delete=models.SET_NULL, verbose_name=_("Question"))
    question_max_score = models.IntegerField(verbose_name=_("Question max score"))
    status = EnumField(submission_statuses, default='WA', verbose_name=_("Status"))

    class Meta(object):
        verbose_name = _("Question report")
        verbose_name_plural = _("Question reports")
