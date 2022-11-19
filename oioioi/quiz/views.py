import datetime
import random

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists, can_enter_contest, is_contest_admin
from oioioi.quiz.forms import QuizForm
from oioioi.quiz.models import QuizSubmission, QuizUserAnswer, QuizQuestion, QuizAnswer
from oioioi.quiz.utils import get_quiz, quiz_exists, user_get_score, user_get_attempts, can_solve_quiz, \
    get_user_possible_attempts, can_see_quiz
from oioioi.rankings.models import Ranking


@menu_registry.register_decorator(
    _("Quiz"),
    lambda request: reverse(
        'quiz',
        kwargs={'contest_id': request.contest.id}),
    order=250)
@enforce_condition(contest_exists & quiz_exists & (is_contest_admin | (can_enter_contest & can_see_quiz)))
def quiz_view(request):
    return TemplateResponse(request, 'quiz/main.html', {
        'time': get_quiz(request).time,
        'start': get_quiz(request).start_date,
        'end': get_quiz(request).end_date,
        'score': user_get_score(request),
        'can_solve': can_solve_quiz(request),
        'attempts_left': user_get_attempts(request),
    })


@enforce_condition(contest_exists & quiz_exists & (is_contest_admin | (can_enter_contest & can_solve_quiz)))
def quiz_solve(request):
    if request.method == 'POST':
        submission = get_user_possible_attempts(request).order_by('id').last()
        if not submission:
            raise PermissionDenied(_("Time's up!"))

        submission.end_date = datetime.datetime.now()

        points = 0

        try:
            points_per_question = submission.quiz.max_points / submission.quiz.questions
        except ZeroDivisionError:
            points_per_question = 0

        for i, user_answer in enumerate(submission.user_answers.order_by('id')):
            try:
                answer = QuizAnswer.objects.get(pk=request.POST['question {}'.format(i)])
                if answer.question == user_answer.question:
                    user_answer.answer = answer
                    user_answer.save(update_fields=['answer'])

                if answer.is_correct:
                    points += points_per_question
            except (ValueError, QuizAnswer.DoesNotExist, MultiValueDictKeyError):
                pass

        submission.score = int(points)
        submission.save(update_fields=['score'])
        Ranking.invalidate_contest(submission.quiz.contest)

        return redirect('quiz')

    submission = QuizSubmission.objects.create(quiz=get_quiz(request), user=request.real_user)
    for question in random.sample(QuizQuestion.objects.all(), submission.quiz.questions):
        QuizUserAnswer.objects.create(submission=submission, question=question)

    form = QuizForm(instance=submission)

    return TemplateResponse(request, 'quiz/solve.html', {
        'time': submission.quiz.time,
        'form': form,
    })
