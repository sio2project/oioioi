from django import forms
from django.core.urlresolvers import reverse
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from oioioi.problems.controllers import ProblemController
from oioioi.quizzes.models import QuizAnswer, QuizSubmission, \
    QuizSubmissionAnswer


class QuizProblemController(ProblemController):
    """Defines rules for quizzes."""

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        pass

    def adjust_problem(self):
        """Called whan a (usually new) problem has just got the controller
           attached or after the problem has been modified.
        """
        pass

    def judge(self, submission, extra_args=None, is_rejudge=False):
        # TODO
        pass

    def update_user_result_for_problem(self, result):
        # TODO
        pass

    def update_user_results(self, user, problem_instance):
        # TODO
        pass

    def _form_field_id_for_question(self, problem_instance, question):
        return 'quiz_' + str(problem_instance.id) + '_q_' + str(question.id)

    def validate_submission_form(self, request, problem_instance, form,
                                 cleaned_data):
        questions = problem_instance.problem.quiz.quizquestion_set.all()
        for question in questions:
            field_name = self._form_field_id_for_question(problem_instance,
                                                          question)
            if field_name in form.errors.as_data():
                continue  # already has a validation error

            if cleaned_data[field_name] == '':
                form.add_error(field_name, _("Answer is required here."))

            # Don't need to check if the answer id is valid,
            #  because ChoiceField handles this.

        return cleaned_data

    def adjust_submission_form(self, request, form, problem_instance):
        questions = problem_instance.problem.quiz.quizquestion_set.all()

        for question in questions:
            answers = question.quizanswer_set.values_list('id', 'answer')
            field_name = self._form_field_id_for_question(problem_instance,
                                                          question)
            if question.is_multiple_choice:
                form.fields[field_name] = forms.MultipleChoiceField(
                    label=question.question,
                    choices=answers,
                    widget=forms.CheckboxSelectMultiple,
                    required=False
                )
            else:
                form.fields[field_name] = forms.ChoiceField(
                    label=question.question,
                    choices=answers,
                    widget=forms.RadioSelect,
                    required=False
                )
            form.set_custom_field_attributes(field_name, problem_instance)

    def create_submission(self, request, problem_instance, form_data,
                          **kwargs):
        judge_after_create = kwargs.get('judge_after_create', True)

        with transaction.atomic():
            submission = QuizSubmission(
                user=form_data.get('user', request.user),
                problem_instance=problem_instance,
                kind=form_data.get('kind',
                                   problem_instance.controller.get_default_submission_kind(
                                       request,
                                       problem_instance=problem_instance)),
                date=request.timestamp
            )

            submission.save()

            # add answers to submission
            questions = problem_instance.problem.quiz.quizquestion_set.all()
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
        for aid, selected in answers.iteritems():
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

    def render_submission(self, request, submission):
        raise NotImplementedError("TODO "
                                  "show score and selected answers in report")

    def get_extra_problem_site_actions(self, problem):
        parent_extras = super(QuizProblemController, self)\
            .get_extra_problem_site_actions(problem)
        change_url = reverse('oioioiadmin:quizzes_quiz_change',
                             args=[problem.quiz.pk])
        return parent_extras + [(change_url, _("Edit questions"))]
