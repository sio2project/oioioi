from django.http import Http404
from django.shortcuts import get_object_or_404
from oioioi.base.utils.api import make_path_coreapi_schema
from oioioi.contests.forms import SubmissionFormForProblemInstance
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.contests.serializers import SubmissionSerializer
from oioioi.contests.utils import contest_exists, can_enter_contest, visible_contests, visible_rounds
from oioioi.problems.models import Problem, ProblemInstance
from oioioi.contests.models import Round
from oioioi.base.permissions import enforce_condition, not_anonymous

from rest_framework import permissions, status, views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema
from rest_framework import serializers
from rest_framework.decorators import api_view

class ContestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contest
        fields = ['id', 'name']


@api_view(['GET'])
@enforce_condition(not_anonymous, login_redirect=False)
def contest_list(request):
    contests = visible_contests(request)
    serializer = ContestSerializer(contests, many=True)
    return Response(serializer.data)

class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = ['__all__']


@api_view(['GET'])
@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
def round_list(request):
    rounds = visible_rounds(request)
    serializer = RoundSerializer(rounds, many=True)
    return Response(serializer.data)

#     # Problem statements in order
#     # 1) problem instance
#     # 2) statement_visible
#     # 3) round end time
#     # 4) user result
#     # 5) number of submissions left
#     # 6) submissions_limit
#     # 7) can_submit
#     # Sorted by (start_date, end_date, round name, problem name)
#     problems_statements = sorted(
#         [
#             (
#                 pi,
#                 controller.can_see_statement(request, pi),
#                 controller.get_round_times(request, pi.round),
#                 # Because this view can be accessed by an anynomous user we can't
#                 # use `user=request.user` (it would cause TypeError). Surprisingly
#                 # using request.user.id is ok since for AnynomousUser id is set
#                 # to None.
#                 next(
#                     (
#                         r
#                         for r in UserResultForProblem.objects.filter(
#                             user__id=request.user.id, problem_instance=pi
#                         )
#                         if r
#                         and r.submission_report
#                         and controller.can_see_submission_score(
#                             request, r.submission_report.submission
#                         )
#                     ),
#                     None,
#                 ),
#                 pi.controller.get_submissions_left(request, pi),
#                 pi.controller.get_submissions_limit(request, pi),
#                 controller.can_submit(request, pi) and not is_contest_archived(request),
#             )
#             for pi in problem_instances
#         ],
#         key=lambda p: (p[2].get_key_for_comparison(), p[0].round.name, p[0].short_name),
#     )

#     show_submissions_limit = any([p[5] for p in problems_statements])
#     show_submit_button = any([p[6] for p in problems_statements])
#     show_rounds = len(frozenset(pi.round_id for pi in problem_instances)) > 1
#     table_columns = 3 + int(show_submissions_limit) + int(show_submit_button)

#     return TemplateResponse(
#         request,
#         'contests/problems_list.html',
#         {
#             'problem_instances': problems_statements,
#             'show_rounds': show_rounds,
#             'show_scores': request.user.is_authenticated,
#             'show_submissions_limit': show_submissions_limit,
#             'show_submit_button': show_submit_button,
#             'table_columns': table_columns,
#             'problems_on_page': getattr(settings, 'PROBLEMS_ON_PAGE', 100),
#         },
#     )
#     rounds = [x.contest for x in request.user.contestview_set.all()]
#     serializer = RoundSerializer(rounds, many=True)
#     return Response(serializer.data)


class CanEnterContest(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_enter_contest(request)


class GetProblemIdView(views.APIView):
    permission_classes = (
        IsAuthenticated,
        CanEnterContest,
    )
    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='contest_id',
                title="Contest id",
                description="Id of the contest to which the problem you want to "
                "query belongs. You can find this id after /c/ in urls "
                "when using SIO 2 web interface.",
            ),
            make_path_coreapi_schema(
                name='problem_short_name',
                title="Problem short name",
                description="Short name of the problem you want to query. "
                "You can find it for example the in first column "
                "of the problem list when using SIO 2 web interface.",
            ),
        ]
    )

    def get(self, request, contest_id, problem_short_name):
        """This endpoint allows you to get id of the particular problem along
        with id of its corresponding problem's instance, given id of the certain
        contest and short name of that problem.
        """
        contest = get_object_or_404(Contest, id=contest_id)
        problem_instance = get_object_or_404(
            ProblemInstance, contest=contest, problem__short_name=problem_short_name
        )
        problem = problem_instance.problem
        response_data = {
            'problem_id': problem.id,
            'problem_instance_id': problem_instance.id,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class SubmitSolutionView(views.APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    def get_problem_instance(self, **kwargs):
        raise NotImplemented

    def post(self, request, **kwargs):
        """This endpoint allows you to submit solution for selected problem."""
        pi = self.get_problem_instance(**kwargs)
        serializer = SubmissionSerializer(pi=pi, data=request.data)

        serializer.is_valid(raise_exception=True)
        form = SubmissionFormForProblemInstance(
            request,
            serializer.problem_instance,
            serializer.validated_data,
            request.FILES,
        )
        if not form.is_valid():
            return Response(form.errors, status=400)

        submission = serializer.problem_instance.controller.create_submission(
            request, form.cleaned_data['problem_instance'], form.cleaned_data
        )

        return Response(submission.id)


class SubmitContestSolutionView(SubmitSolutionView):
    permission_classes = (
        IsAuthenticated,
        CanEnterContest,
    )
    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='contest_name',
                title="Contest name",
                description="Name of the contest to which you want to submit "
                "a solution. You can find it after /c/ in urls "
                "when using the SIO2 web interface.",
            ),
            make_path_coreapi_schema(
                name='problem_short_name',
                title="Problem short name",
                description="Short name of the problem to which you want to submit "
                "solution. You can find it for example in the first column "
                "of the problem list when using SIO 2 web interface.",
            ),
        ]
    )

    def get_problem_instance(self, contest_name, problem_short_name):
        return get_object_or_404(
            ProblemInstance, contest=contest_name, short_name=problem_short_name
        )


class SubmitProblemsetSolutionView(SubmitSolutionView):
    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='problem_site_key',
                title="Problem site key",
                description="This is unique key for the problem in problemset. "
                "You can find it after /problemset/problem/ in url of "
                "any site related to the problem when using the SIO2 web "
                "interface.",
            ),
        ]
    )

    def get_problem_instance(self, problem_site_key):
        problem = get_object_or_404(Problem, problemsite__url_key=problem_site_key)
        pi = problem.main_problem_instance
        if not pi:
            raise Http404
        return pi
