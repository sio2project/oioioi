import json
import types
from collections import defaultdict
from datetime import datetime, timedelta  # pylint: disable=E0611

from django.conf import settings
from django.contrib.auth.models import User
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.contests.controllers import (
    PublicContestRegistrationController,
    submission_template_context,
)
from oioioi.contests.models import (
    ProblemInstance,
    Round,
    Submission,
    UserResultForContest,
    UserResultForProblem,
)
from oioioi.contests.permissions import can_create_contest
from oioioi.contests.utils import (
    can_admin_contest,
    contest_exists,
    has_any_contest,
    is_contest_basicadmin,
    rounds_times,
    visible_contests,
)
from oioioi.dashboard.contest_dashboard import register_contest_dashboard_view
from oioioi.portals.conditions import main_page_from_default_global_portal
from oioioi.portals.models import Portal
from oioioi.problems.utils import can_admin_problem
from oioioi.programs.admin import ValidationFormset
from oioioi.programs.models import Test
from oioioi.questions.models import Message
from oioioi.questions.views import messages_template_context, visible_messages
from oioioi.simpleui.forms import ProblemInstanceForm, TestForm

NUMBER_OF_RECENT_ACTIONS = 5
RECENT_ACTIVITY_DAYS = 7
MAX_CONTESTS_ON_PAGE = 6


def score_report_is_valid(score_report):
    return (
        score_report is not None
        and score_report.score is not None
        and score_report.max_score is not None
    )


def get_round_context(request, round_pk):
    selected_round = get_object_or_404(Round, pk=round_pk)

    round = {'round': selected_round, 'problem_instances': []}

    problem_instances = {}

    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(round=selected_round).select_related(
        'problem'
    )

    visible_problem_instances = [
        pi for pi in queryset if controller.can_see_problem(request, pi)
    ]

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

    questions = Message.objects.filter(round=selected_round, date__range=last_week)

    for question in questions:
        if question.problem_instance is not None:
            problem_instance = problem_instances[question.problem_instance.pk]
            problem_instance['question_count'] += 1

    submissions = Submission.objects.filter(
        problem_instance__round=selected_round, date__range=last_week
    )

    for submission in submissions:
        problem_instance = problem_instances[submission.problem_instance.pk]
        problem_instance['submission_count'] += 1

    results = UserResultForProblem.objects.filter(
        problem_instance__round=selected_round, submission_report__isnull=False
    )

    for result in results:
        problem_instance = problem_instances[result.problem_instance.pk]
        score_report = result.submission_report.score_report

        if score_report_is_valid(score_report):
            problem_instance['max_score'] = score_report.max_score.to_int()

            problem_instance['tried_solving_count'] += 1
            if score_report.score == score_report.max_score:
                problem_instance['solved_count'] += 1

            problem_instance['users_with_score'][score_report.score.to_int()] += 1

    contest_data = {}

    for _, pi in problem_instances.items():
        scores = []

        for score, users_with_score in pi['users_with_score'].items():
            scores.append([score, users_with_score])

        if pi['tried_solving_count'] == 0:
            pi['solved'] = 'none'
        else:
            solved_ratio = float(pi['solved_count']) / pi['tried_solving_count']

            if solved_ratio < 1.0 / 3:
                pi['solved'] = 'low'
            elif solved_ratio < 2.0 / 3:
                pi['solved'] = 'medium'
            else:
                pi['solved'] = 'high'

        pi['users_with_score'] = scores

        contest_data[pi['problem_instance'].short_name] = {
            'scores': scores,
            'max_score': pi['max_score'],
        }

        round['problem_instances'].append(pi)

    return {
        'selected_round': round,
        'contest_data': json.dumps(contest_data),
        'RECENT_ACTIVITY_DAYS': RECENT_ACTIVITY_DAYS,
    }


@enforce_condition(contest_exists & is_contest_basicadmin)
def contest_dashboard_view(request, round_pk=None):
    if request.user.is_superuser:
        return redirect('default_contest_view', contest_id=request.contest.id)

    messages = messages_template_context(request, visible_messages(request))[
        :NUMBER_OF_RECENT_ACTIONS
    ]

    queryset = (
        Submission.objects.filter(problem_instance__contest=request.contest)
        .order_by('-date')
        .select_related(
            'user',
            'problem_instance',
            'problem_instance__contest',
            'problem_instance__round',
            'problem_instance__problem',
        )
        .prefetch_related('problem_instance__problem__names')
    )

    ss = [
        submission_template_context(request, s, skip_valid_kinds=True)
        for s in queryset[:NUMBER_OF_RECENT_ACTIONS]
    ]

    rtimes = list(rounds_times(request, request.contest).items())
    rtimes.sort(key=lambda r_rt: r_rt[0].start_date)

    if round_pk is None and len(rtimes) > 0:
        # First active round, or last one if there are no active ones
        round_pk = next(
            ((r, rt) for r, rt in rtimes if rt.is_active(request.timestamp)), rtimes[-1]
        )[0].pk

    context = {
        'round_times': rtimes,
        'selected_round': None,
        'records': messages,
        'submissions': ss,
        'contest_dashboard_url_name': 'simpleui_contest_dashboard',
        'public_contest': isinstance(
            request.contest.controller.registration_controller(),
            PublicContestRegistrationController,
        ),
    }

    if round_pk is not None:
        context.update(get_round_context(request, round_pk))

    return TemplateResponse(request, 'simpleui/contest/contest.html', context)


@enforce_condition(can_create_contest | has_any_contest)
def user_dashboard_view(request):
    contest_context = []
    min_date = datetime.today() - timedelta(days=7)

    contests = [contest for contest in visible_contests(request)]
    are_contests_limited = len(contests) > MAX_CONTESTS_ON_PAGE
    visible_contests_count = len(contests)

    contests = [x for x in contests if can_admin_contest(request.user, x)]
    if len(contests) < visible_contests_count:
        are_contests_limited = True
    contests.sort(key=lambda x: x.creation_date, reverse=True)

    contests = contests[:MAX_CONTESTS_ON_PAGE]

    if 'oioioi.portals' in settings.INSTALLED_APPS:
        has_portal = main_page_from_default_global_portal(request)
    else:
        has_portal = False

    for contest in contests:
        scores = [
            result.score.to_int()
            for result in UserResultForContest.objects.filter(contest=contest).all()
            if result.score is not None
        ]

        max_score = 0
        for problem_inst in ProblemInstance.objects.filter(contest=contest):
            user_results = UserResultForProblem.objects.filter(
                problem_instance=problem_inst, submission_report__isnull=False
            )
            if user_results.count() > 0:
                for result in user_results:
                    score_report = result.submission_report.score_report

                    if score_report_is_valid(score_report):
                        max_score += score_report.max_score.to_int()
                        break

        contest_dict = {
            'id': contest.id,
            'name': contest.name,
            'round_count': Round.objects.filter(contest=contest).count(),
            'task_count': ProblemInstance.objects.filter(contest=contest).count(),
            'submission_count': Submission.objects.filter(
                problem_instance__contest=contest
            ).count(),
            'recent_submission_count': Submission.objects.filter(
                problem_instance__contest=contest, date__gte=min_date
            ).count(),
            'recent_question_count': Message.objects.filter(
                contest=contest, kind='QUESTION', date__gte=min_date
            ).count(),
            'max_score': max_score,
            'scores': scores,
            'contest_controller': contest.controller,
            'dashboard_url': reverse(
                'simpleui_contest_dashboard', kwargs={'contest_id': contest.id}
            ),
            'public_contest': isinstance(
                contest.controller.registration_controller(),
                PublicContestRegistrationController,
            ),
        }

        if not contest_dict['public_contest']:
            contest_dict['user_count'] = (
                contest.controller.registration_controller()
                .filter_participants(User.objects.all())
                .count()
            )

        contest_context.append(contest_dict)
    context = {
        'contests': contest_context,
        'are_contests_limited': are_contests_limited,
        'has_portal': has_portal,
        'can_create_contest': can_create_contest(request),
    }
    if has_portal:
        context['portal_path'] = Portal.objects.filter(owner=None, link_name='default')[
            0
        ].root.get_path()

    return TemplateResponse(request, 'simpleui/main_dashboard/dashboard.html', context)


@enforce_condition(contest_exists & is_contest_basicadmin)
def problem_settings(request, problem_instance_id):
    pi = get_object_or_404(
        ProblemInstance, id=problem_instance_id, contest=request.contest
    )
    problem = pi.problem
    tests = pi.test_set.all()

    TestFormset = modelformset_factory(Test, form=TestForm, extra=0)
    ProblemInstanceFormset = modelformset_factory(
        ProblemInstance, form=ProblemInstanceForm, extra=0
    )

    if request.method == 'POST':
        pi_formset = ProblemInstanceFormset(request.POST, prefix='pif')

        test_formset = TestFormset(request.POST)
        # Bind the clean method, which serves as a time limit and max
        # scores equality validator.
        # http://stackoverflow.com/questions/9646187
        test_formset.get_time_limit_sum = types.MethodType(
            ValidationFormset.__dict__['get_time_limit_sum'], test_formset
        )
        test_formset.validate_time_limit_sum = types.MethodType(
            ValidationFormset.__dict__['validate_time_limit_sum'], test_formset
        )
        test_formset.validate_max_scores_in_group = types.MethodType(
            ValidationFormset.__dict__['validate_max_scores_in_group'], test_formset
        )
        test_formset.clean = types.MethodType(
            ValidationFormset.__dict__['clean'], test_formset
        )

        if pi_formset.is_valid() and test_formset.is_valid():
            pi_formset.save()
            test_formset.save()

            return redirect(
                reverse(
                    'simpleui_problem_settings',
                    kwargs={'problem_instance_id': problem_instance_id},
                )
            )

        test_forms = test_formset
        pi_form = pi_formset
    else:
        test_forms = TestFormset(queryset=tests)
        pi_form = ProblemInstanceFormset(
            queryset=ProblemInstance.objects.filter(id=pi.id),
            prefix='pif',
        )

    context = {
        'problem_instance': pi,
        'problem': problem,
        'can_admin_problem': can_admin_problem(request, problem),
        'tests': tests,
        'pi_form': pi_form,
        'test_forms': test_forms,
    }

    return TemplateResponse(request, 'simpleui/problem_settings/settings.html', context)


@register_contest_dashboard_view(
    order=100, condition=(contest_exists & is_contest_basicadmin & ~is_superuser)
)
def contest_dashboard_redirect(request):
    return redirect(
        reverse('simpleui_contest_dashboard', kwargs={'contest_id': request.contest.id})
    )
