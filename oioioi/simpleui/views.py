import json
from collections import defaultdict
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from oioioi.base.main_page import register_main_page_view
from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import Round, ProblemInstance, Submission, \
    UserResultForContest, UserResultForProblem
from oioioi.contests.utils import contest_exists, is_contest_admin, \
    rounds_times, visible_contests, can_admin_contest
from oioioi.dashboard.contest_dashboard import register_contest_dashboard_view
from oioioi.portals.conditions import global_portal_exists
from oioioi.portals.models import Portal
from oioioi.questions.models import Message
from oioioi.questions.views import messages_template_context, visible_messages
from oioioi.teachers.views import is_teachers_contest, is_teacher, is_teachers

NUMBER_OF_RECENT_ACTIONS = 5
RECENT_ACTIVITY_DAYS = 7
MAX_CONTESTS_ON_PAGE = 6


@register_main_page_view(order=400, condition=is_teacher & ~is_superuser)
def main_page_view(request):
    return redirect('teacher_dashboard')


def get_round_context(request, round_pk):
    selected_round = get_object_or_404(Round, pk=round_pk)

    round = {}

    round['round'] = selected_round
    round['problem_instances'] = []

    problem_instances = {}

    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(round=selected_round) \
        .select_related('problem')

    visible_problem_instances = [pi for pi in queryset if
                                 controller.can_see_problem(request, pi)]

    for pi in visible_problem_instances:
        problem_instances[pi.pk] = {}
        problem_instances[pi.pk]['problem_instance'] = pi
        problem_instances[pi.pk]['submission_count'] = 0
        problem_instances[pi.pk]['question_count'] = 0
        problem_instances[pi.pk]['solved_count'] = 0
        problem_instances[pi.pk]['tried_solving_count'] = 0
        problem_instances[pi.pk]['users_with_score'] = defaultdict(int)
        problem_instances[pi.pk]['max_score'] = 0

    end_date = request.timestamp
    start_date = end_date - timedelta(days=RECENT_ACTIVITY_DAYS)

    last_week = [start_date, end_date]

    questions = Message.objects.filter(
        round=selected_round, date__range=last_week)

    for question in questions:
        if question.problem_instance is not None:
            problem_instance = problem_instances[question.problem_instance.pk]
            problem_instance['question_count'] += 1

    submissions = Submission.objects.filter(
        problem_instance__round=selected_round, date__range=last_week)

    for submission in submissions:
        problem_instance = problem_instances[submission.problem_instance.pk]
        problem_instance['submission_count'] += 1

    results = UserResultForProblem.objects.filter(
        problem_instance__round=selected_round,
        submission_report__isnull=False)

    for result in results:
        problem_instance = problem_instances[result.problem_instance.pk]
        score_report = result.submission_report.score_report

        problem_instance['max_score'] = score_report.max_score.to_int()

        problem_instance['tried_solving_count'] += 1
        if score_report.score == score_report.max_score:
            problem_instance['solved_count'] += 1

        problem_instance['users_with_score'][score_report.score.to_int()] += 1

    contest_data = {}

    for _, pi in problem_instances.items():
        scores = []

        for score, users_with_score in pi['users_with_score'].iteritems():
            scores.append([score, users_with_score])

        if pi['tried_solving_count'] == 0:
            pi['solved'] = 'none'
        else:
            solved_ratio = float(pi['solved_count']) \
                           / pi['tried_solving_count']

            if solved_ratio < 1. / 3:
                pi['solved'] = 'low'
            elif solved_ratio < 2. / 3:
                pi['solved'] = 'medium'
            else:
                pi['solved'] = 'high'

        pi['users_with_score'] = scores

        contest_data[pi['problem_instance'].short_name] = {
            'scores': scores,
            'max_score': pi['max_score']
        }

        round['problem_instances'].append(pi)

    return {
        'selected_round': round,
        'contest_data': json.dumps(contest_data),
        'RECENT_ACTIVITY_DAYS': RECENT_ACTIVITY_DAYS
    }


@register_contest_dashboard_view(order=50, condition=(contest_exists &
                                 is_teachers_contest & is_contest_admin &
                                 ~is_superuser))
def contest_dashboard_redirect(request):
    return redirect(reverse('teacher_contest_dashboard',
                            kwargs={'contest_id': request.contest.id}))


@enforce_condition(contest_exists & is_teachers_contest & is_contest_admin)
def contest_dashboard_view(request, round_pk=None):
    messages = messages_template_context(request, visible_messages(request))[
               :NUMBER_OF_RECENT_ACTIONS]

    queryset = Submission.objects \
        .filter(problem_instance__contest=request.contest) \
        .order_by('-date') \
        .select_related('user', 'problem_instance',
                        'problem_instance__contest',
                        'problem_instance__round',
                        'problem_instance__problem')

    ss = [submission_template_context(request, s) for s in
          queryset[:NUMBER_OF_RECENT_ACTIONS]]

    rtimes = rounds_times(request).items()
    rtimes.sort(key=lambda (r, rt): r.start_date)

    if round_pk is None and len(rtimes) > 0:
        # First active round, or last one if there are no active ones
        round_pk = next(
            ((r, rt) for r, rt in rtimes if rt.is_active(request.timestamp)),
            rtimes[-1])[0].pk

    context = {
        'round_times': rtimes,
        'selected_round': None,
        'records': messages,
        'submissions': ss
    }

    if round_pk is not None:
        context.update(get_round_context(request, round_pk))

    return TemplateResponse(request, 'simpleui/contest/contest.html', context)


@enforce_condition(is_teacher)
def teacher_dashboard_view(request):
    contest_context = []
    min_date = datetime.today() - timedelta(days=7)

    contests = [contest for contest in visible_contests(request)]
    are_contests_limited = len(contests) > MAX_CONTESTS_ON_PAGE
    visible_contests_count = len(contests)

    contests = [x for x in contests if is_teachers(x)
                                    and can_admin_contest(request.user, x)]
    if len(contests) < visible_contests_count:
        are_contests_limited = True
    contests.sort(key=lambda x: x.creation_date, reverse=True)

    contests = contests[:MAX_CONTESTS_ON_PAGE]

    if 'oioioi.portals' in settings.INSTALLED_APPS:
        has_portal = global_portal_exists(request)
    else:
        has_portal = False

    for contest in contests:

        scores = [result.score.to_int() for result in
                    UserResultForContest.objects.filter(contest=contest).all()]

        max_score = 0
        for problem_inst in ProblemInstance.objects.filter(contest=contest):
            user_results = \
                UserResultForProblem.objects.filter(
                        problem_instance=problem_inst).all()
            if user_results.count() > 0:
                max_score += user_results[0].submission_report.score_report. \
                                                             max_score.to_int()

        contest_dict = {
            'id': contest.id,
            'name': contest.name,
            'round_count': Round.objects.filter(contest=contest).count(),
            'task_count': ProblemInstance.objects.filter(
                contest=contest).count(),
            'user_count': User.objects.filter(
                participant__contest=contest).count(),
            'submission_count': Submission.objects.filter(
                problem_instance__contest=contest).count(),
            'recent_submission_count': Submission.objects.filter(
                    problem_instance__contest=contest, date__gte=min_date
                ).count(),
            'recent_question_count': Message.objects.filter(
                    contest=contest, kind='QUESTION', date__gte=min_date
                ).count(),
            'max_score': max_score,
            'scores': scores,
        }
        contest_context.append(contest_dict)
    context = {
            'contests': contest_context,
            'are_contests_limited': are_contests_limited,
            'has_portal': has_portal
    }
    if has_portal:
        context['portal_path'] = Portal.objects.filter(owner=None)[0] \
                                 .root.get_path()

    return TemplateResponse(request,
            'simpleui/main_dashboard/dashboard.html', context)
