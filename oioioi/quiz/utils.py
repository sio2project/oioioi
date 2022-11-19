import datetime

from django.contrib.auth.models import User
from django.db.models import Max
from django.utils import timezone

from oioioi.base.permissions import make_request_condition
from oioioi.quiz.models import QuizInstance, QuizSubmission


@make_request_condition
def quiz_exists(request):
    return QuizInstance.objects.filter(contest=request.contest).exists()


@make_request_condition
def can_see_quiz(request):
    return not request.user.is_anonymous() and \
           request.contest.controller.registration_controller() \
               .filter_participants(User.objects.filter(pk=request.user.pk)).exists()


@make_request_condition
def can_solve_quiz(request):
    return can_see_quiz(request) and \
           ((user_get_attempts(request) > 0 and get_quiz(request).is_open())
            or user_can_submit_last_attempt(request))


def get_quiz(request):
    return QuizInstance.objects.get(contest=request.contest)


def user_get_score(request):
    return QuizSubmission.objects \
        .filter(quiz=get_quiz(request), user=request.user) \
        .aggregate(best_score=Max('score'))['best_score']


def user_get_score_for_contest(contest, user):
    quiz = QuizInstance.objects.get(contest=contest)

    return QuizSubmission.objects \
        .filter(quiz=quiz, user=user) \
        .aggregate(best_score=Max('score'))['best_score']


def user_get_attempts(request):
    submissions = QuizSubmission.objects.filter(quiz=get_quiz(request), user=request.user).count()
    max_attempts = QuizInstance.objects.get(contest=request.contest).attempts
    return max_attempts - submissions


def user_can_submit_last_attempt(request):
    return request.method == 'POST' and get_user_possible_attempts(request).exists()


def get_user_possible_attempts(request):
    quiz = get_quiz(request)

    return QuizSubmission.objects.filter(
        quiz=quiz,
        user=request.user,
        end_date__isnull=True,
        start_date__gte=timezone.now() - datetime.timedelta(minutes=quiz.time)
    )
