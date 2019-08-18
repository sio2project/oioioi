import six
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import SubmissionReport, ScoreReport
from oioioi.problems.controllers import ProblemController
from oioioi.problems.utils import can_admin_problem_instance
from oioioi.quizzes.models import QuizAnswer, QuizSubmission, \
    QuizSubmissionAnswer, QuestionReport


class QuizProblemController(ProblemController):
    """Defines rules for quizzes."""

    def adjust_problem(self):
        """Called whan a (usually new) problem has just got the controller
           attached or after the problem has been modified.
        """
        pass

    def _form_field_id_for_question(self, problem_instance, question):
        return 'quiz_' + str(problem_instance.id) + '_q_' + str(question.id)

    def validate_submission_form(self, request, problem_instance, form,
                                 cleaned_data):
        for question in self.select_questions(request.user, problem_instance, None):
            field_name = self._form_field_id_for_question(problem_instance,
                                                          question)
            if field_name in form.errors.as_data():
                continue  # already has a validation error

            if cleaned_data[field_name] == '':
                form.add_error(field_name, _("Answer is required here."))

            # Don't need to check if the answer id is valid,
            #  because ChoiceField handles this.

        return cleaned_data

    def render_question(self, request, question):
        return render_to_string('quizzes/question.html', request=request, context={'question': question})

    def render_answer(self, request, answer):
        return render_to_string('quizzes/answer.html', request=request, context={'answer': answer})

    def add_question_to_form(self, request, form, problem_instance, question):
        answers = [(a.id, self.render_answer(request, a)) for a in question.quizanswer_set.all()]
        field_name = self._form_field_id_for_question(problem_instance, question)
        label = self.render_question(request, question)

        if question.is_multiple_choice:
            form.fields[field_name] = forms.MultipleChoiceField(
                label=label,
                choices=answers,
                widget=forms.CheckboxSelectMultiple,
                required=False
            )
        else:
            form.fields[field_name] = forms.ChoiceField(
                label=label,
                choices=answers,
                widget=forms.RadioSelect,
                required=False
            )
        form.set_custom_field_attributes(field_name, problem_instance)

    def select_questions(self, user, problem_instance, submission):
        return problem_instance.problem.quiz.quizquestion_set.all()

    def adjust_submission_form(self, request, form, problem_instance):
        questions = self.select_questions(request.user, problem_instance, None)

        for question in questions:
            self.add_question_to_form(request, form, problem_instance, question)

    def create_submission(self, request, problem_instance, form_data,
                          **kwargs):
        judge_after_create = kwargs.get('judge_after_create', True)

        with transaction.atomic():
            questions = self.select_questions(form_data.get('user', request.user), problem_instance, None)

            submission = QuizSubmission(
                user=form_data.get('user', request.user),
                problem_instance=problem_instance,
                kind=form_data.get('kind',
                                   problem_instance.controller.
                                   get_default_submission_kind(request,
                                                               problem_instance=problem_instance)),
                date=request.timestamp
            )

            submission.save()

            # add answers to submission
            for question in questions:
                field_id = self._form_field_id_for_question(problem_instance,
                                                            question)

                selected_answers = self._get_selected_answers(form_data,
                                                              field_id,
                                                              question)
                self._submit_answers(selected_answers, question,
                                     submission)

        if judge_after_create:
            problem_instance.controller.judge(submission)
        return submission

    def _submit_answers(self, selected_answers, question,
                        submission):

        answers = {a.id: (a.id in selected_answers)
                   for a in question.quizanswer_set.all()}
        for aid, selected in six.iteritems(answers):
            answer = QuizAnswer.objects.get(id=aid)
            sub = QuizSubmissionAnswer.objects.create(
                quiz_submission=submission,
                answer=answer,
                is_selected=selected
            )
            sub.save()

    def _get_selected_answers(self, form_data, field_id, question):
        field_value = form_data.get(field_id)
        if question.is_multiple_choice:
            return [int(a) for a in field_value]
        else:
            return [int(field_value)]

    def mixins_for_admin(self):
        from oioioi.quizzes.admin import QuizAdminMixin
        return super(QuizProblemController, self).mixins_for_admin() \
               + (QuizAdminMixin,)

    def get_extra_problem_site_actions(self, problem):
        parent_extras = super(QuizProblemController, self)\
            .get_extra_problem_site_actions(problem)
        change_url = reverse('oioioiadmin:quizzes_quiz_change',
                             args=[problem.quiz.pk])
        return parent_extras + [(change_url, _("Edit questions"))]

    def render_report(self, request, report):
        problem_instance = report.submission.problem_instance
        score_report = ScoreReport.objects.get(submission_report=report)
        picontroller = problem_instance.controller
        question_reports = QuestionReport.objects.filter(
            submission_report=report) \
            .order_by('question__order')

        return render_to_string('quizzes/report.html',
                                request=request,
                                context={
                                    'report': report,
                                    'score_report': score_report,
                                    'question_reports': question_reports,
                                    'is_admin': picontroller.is_admin(
                                        request,
                                        report)
                                })

    def render_submission(self, request, submission):
        problem_instance = submission.problem_instance
        can_admin = \
            can_admin_problem_instance(request, submission.problem_instance)
        context = {
            'submission':
                submission_template_context(request, submission.quizsubmission),
            'supported_extra_args':
                problem_instance.controller.get_supported_extra_args(submission),
            'can_admin': can_admin
        }
        return render_to_string('quizzes/submission_header.html',
                                request=request,
                                context=context)

    def update_submission_score(self, submission):
        try:
            report = SubmissionReport.objects.filter(submission=submission,
                                                     status='ACTIVE',
                                                     kind='NORMAL').get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.status = score_report.status
            submission.score = score_report.score
        except SubmissionReport.DoesNotExist:
            submission.score = None

        submission.save()

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        self.generate_base_environ(environ, submission, **kwargs)

    def generate_base_environ(self, environ, submission, **kwargs):
        self.generate_initial_evaluation_environ(environ, submission)
        environ.setdefault('recipe', []).append(
                ('score_quiz',
                    'oioioi.quizzes.handlers.score_quiz'),
                )

    def generate_initial_evaluation_environ(self, environ, submission,
                                            **kwargs):
        problem_instance = submission.problem_instance
        problem = problem_instance.problem
        contest = problem_instance.contest
        if contest is not None:
            round = problem_instance.round
            environ['round_id'] = round.id
            environ['contest_id'] = contest.id

        environ['submission_id'] = submission.id
        environ['submission_kind'] = submission.kind
        environ['problem_instance_id'] = problem_instance.id
        environ['problem_id'] = problem.id
        environ['problem_short_name'] = problem.short_name

        environ['submission_owner'] = submission.user.username \
                                      if submission.user else None
        environ['oioioi_instance'] = settings.SITE_NAME
        environ['contest_priority'] = contest.judging_priority \
            if contest is not None else settings.NON_CONTEST_PRIORITY
        environ['contest_priority'] += settings.OIOIOI_INSTANCE_PRIORITY_BONUS
        environ['contest_weight'] = contest.judging_weight \
            if contest is not None else settings.NON_CONTEST_WEIGHT
        environ['contest_weight'] += settings.OIOIOI_INSTANCE_WEIGHT_BONUS

        environ.setdefault('report_kinds', ['NORMAL'])
        if 'hidden_judge' in environ['extra_args']:
            environ['report_kinds'] = ['HIDDEN']

    def supports_problem_statement(self):
        return False
