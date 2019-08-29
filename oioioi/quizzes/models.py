from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

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
    quiz = models.ForeignKey(Quiz, verbose_name=_("Quiz"),
                             on_delete=models.CASCADE)
    order = models.IntegerField(default=0, verbose_name=_("Order"))
    is_text_input = models.BooleanField(default=False, verbose_name=_("Hide answers"), help_text=_("Instead of listing answers, expect the contestant to type in their answer."))
    trim_whitespace = models.BooleanField(default=False, verbose_name=_("Trim leading and trailing whitespace in user input"), help_text=_("Only applies if answers are hidden."))
    ignore_case = models.BooleanField(default=False, verbose_name=_("Match user input case insensitively"), help_text=_("Only applies if answers are hidden."))

    class Meta(object):
        ordering = ['order']
        verbose_name = _("Quiz question")
        verbose_name_plural = _("Quiz questions")


class QuizAnswer(models.Model):
    question = models.ForeignKey(QuizQuestion, verbose_name=_("Question"),
                                 on_delete=models.CASCADE)
    answer = models.TextField(verbose_name=_("Answer"))
    is_correct = models.BooleanField(default=False,
                                     verbose_name=_("Is answer correct"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))

    class Meta(object):
        ordering = ['order']
        verbose_name = _("Quiz answer")
        verbose_name_plural = _("Quiz answers")


class QuizPicture(models.Model):
    caption = models.TextField(verbose_name=_("Caption"), blank=True)
    file = models.FileField(verbose_name=_("Image file"))
    order = models.IntegerField(default=0, verbose_name=_("Order"))

    def get_absolute_url(self):
        raise NotImplementedError

    @property
    def quiz(self):
       raise NotImplementedError

    class Meta(object):
        abstract = True
        ordering = ['order']


class QuizQuestionPicture(QuizPicture):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse('picture_view', args=['q', self.id])

    @property
    def quiz(self):
        return self.question.quiz

    class Meta(QuizPicture.Meta):
        verbose_name = _("Quiz question picture")
        verbose_name_plural = _("Quiz question pictures")


class QuizAnswerPicture(QuizPicture):
    answer = models.ForeignKey(QuizAnswer, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse('picture_view', args=['a', self.id])

    @property
    def quiz(self):
        return self.answer.question.quiz

    class Meta(QuizPicture.Meta):
        verbose_name = _("Quiz answer picture")
        verbose_name_plural = _("Quiz answer pictures")


class QuizSubmission(Submission):

    class Meta(object):
        verbose_name = _("Quiz submission")
        verbose_name_plural = _("Quiz submissions")


class QuizSubmissionAnswer(models.Model):
    quiz_submission = models.ForeignKey(QuizSubmission,
                                        verbose_name=_("Quiz submission"),
                                        on_delete=models.CASCADE)
    answer = models.ForeignKey(QuizAnswer, verbose_name=_("Answer"),
                               on_delete=models.SET_NULL, null=True)
    is_selected = models.BooleanField(default=False,
                                      verbose_name=_("Is answer selected"))

    class Meta(object):
        verbose_name = _("Quiz submission answer")
        verbose_name_plural = _("Quiz submission answers")


class QuizSubmissionTextAnswer(models.Model):
    quiz_submission = models.ForeignKey(QuizSubmission,
                                        verbose_name=_("Quiz submission"),
                                        on_delete=models.CASCADE)
    question = models.ForeignKey(QuizQuestion, verbose_name=_("Question"),
                                 on_delete=models.SET_NULL, null=True)
    text_answer = models.TextField(verbose_name=_("Text answer"))

    class Meta(object):
        unique_together = (('quiz_submission', 'question'),)
        verbose_name = _("Quiz submission text answer")
        verbose_name_plural = _("Quiz submission text answers")


class QuestionReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport,
                                          verbose_name=_("Submission report"),
                                          on_delete=models.CASCADE)
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
