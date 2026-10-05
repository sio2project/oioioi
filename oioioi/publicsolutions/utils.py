from oioioi.base.permissions import make_condition, make_request_condition
from oioioi.base.utils import request_cached
from oioioi.contests.models import ProblemInstance, Round, Submission
from oioioi.programs.controllers import ProgrammingContestController


@request_cached
def public_rounds(request):
    controller = request.contest.controller
    return [round for round in Round.objects.filter(contest=request.contest) if controller.can_see_publicsolutions(request, round)]


def filter_public_problem_instances(request, qs):
    return qs.filter(round__in=public_rounds(request))


@request_cached
def public_problem_instances(request):
    return filter_public_problem_instances(request, ProblemInstance.objects.all())


@request_cached
def unfiltered_submissions(request):
    return Submission.objects.filter(problem_instance__in=public_problem_instances(request)).select_related(
        "publication",
        "user",
        "problem_instance",
        "problem_instance__problem",
        "problem_instance__contest",
    )


@request_cached
def get_public_solutions(request):
    return filter_public_solutions(request, unfiltered_submissions(request))


def filter_public_solutions(request, qs):
    cc = request.contest.controller
    return (cc.solutions_must_be_public(qs) | qs.filter(publication__isnull=False)).filter(problem_instance__in=public_problem_instances(request))


@request_cached
def get_may_be_published_solutions(request):
    controller = request.contest.controller
    subs = unfiltered_submissions(request)
    mustbe_subs = controller.solutions_must_be_public(subs)

    return controller.solutions_may_be_published(subs.exclude(id__in=mustbe_subs))


@request_cached
def get_may_be_published_solutions_for_user(request):
    qs = get_may_be_published_solutions(request)
    if request.user.is_anonymous:
        return qs.none()
    return qs.filter(user=request.user)


@request_cached
def problem_instances_with_any_public_solutions(request):
    return public_problem_instances(request).filter(submission__in=(get_public_solutions(request))).distinct()


@make_request_condition
def any_round_public(request):
    return isinstance(request.contest.controller, ProgrammingContestController) and public_rounds(request)


@make_condition()
def solution_may_be_published(request, *args, **kwargs):
    """Checks whether kwargs describe an existing submission
    for which a user has a publication right.

    It assumes user is not anonymous.
    """
    sub_id = kwargs["submission_id"]
    submission = get_may_be_published_solutions(request).filter(pk=sub_id)
    return submission.exists()
