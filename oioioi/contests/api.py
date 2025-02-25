from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from oioioi.base.utils import request_cached
from oioioi.base.utils.api import make_path_coreapi_schema
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.forms import SubmissionFormForProblemInstance
from oioioi.contests.models import Contest, ProblemInstance, Submission
from oioioi.contests.serializers import (
    ContestSerializer,
    ProblemSerializer,
    RoundSerializer,
    SubmissionSerializer,
    UserResultForProblemSerializer,
)
from oioioi.contests.utils import (
    can_enter_contest,
    get_problem_statements,
    visible_contests,
)
from oioioi.default_settings import MIDDLEWARE
from oioioi.problems.models import Problem, ProblemInstance
from oioioi.base.permissions import enforce_condition, not_anonymous

from oioioi.problems.utils import query_statement
from oioioi.programs.models import ProgramSubmission
from oioioi.programs.utils import decode_str, get_submission_source_file_or_error
from rest_framework import permissions, status, views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema
from rest_framework import serializers
from rest_framework.decorators import api_view


@api_view(['GET'])
@enforce_condition(not_anonymous, login_redirect=False)
def contest_list(request):
    contests = visible_contests(request)
    serializer = ContestSerializer(contests, many=True)
    return Response(serializer.data)


class CanEnterContest(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_enter_contest(request)


class UnsafeApiAllowed(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return not any('IpDnsAuthMiddleware' in x for x in MIDDLEWARE)


class GetContestRounds(views.APIView):
    permission_classes = (
        IsAuthenticated,
        CanEnterContest,
    )

    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='contest_id',
                title="Contest id",
                description="Id of the contest from contest_list endpoint",
            ),
        ]
    )

    def get(self, request, contest_id):
        contest = get_object_or_404(Contest, id=contest_id)
        rounds = contest.round_set.all()
        serializer = RoundSerializer(rounds, many=True)
        return Response(serializer.data)


class GetContestProblems(views.APIView):
    permission_classes = (
        IsAuthenticated,
        CanEnterContest,
    )

    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='contest_id',
                title="Contest id",
                description="Id of the contest from contest_list endpoint",
            ),
        ]
    )

    def get(self, request, contest_id):
        contest: Contest = get_object_or_404(Contest, id=contest_id)
        controller = contest.controller
        problem_instances = (
            ProblemInstance.objects.filter(contest=request.contest)
            .select_related('problem')
            .prefetch_related('round')
        )

        # Problem statements in order
        # 0) problem instance
        # 1) statement_visible
        # 2) round end time
        # 3) user result
        # 4) number of submissions left
        # 5) submissions_limit
        # 6) can_submit
        # Sorted by (start_date, end_date, round name, problem name)
        problem_statements = get_problem_statements(
            request, controller, problem_instances
        )

        data = []
        for problem_stmt in problem_statements:
            if problem_stmt[1]:
                serialized = dict(ProblemSerializer(problem_stmt[0], many=False).data)
                serialized["full_name"] = problem_stmt[0].problem.legacy_name
                serialized["user_result"] = UserResultForProblemSerializer(
                    problem_stmt[3], many=False
                ).data
                serialized["submissions_left"] = problem_stmt[4]
                serialized["can_submit"] = problem_stmt[6]
                serialized["statement_extension"] = (
                    st.extension
                    if (st := query_statement(problem_stmt[0].problem))
                    else None
                )
                data.append(serialized)

        return Response(data)


class GetUserProblemSubmissionList(views.APIView):
    permission_classes = (IsAuthenticated, CanEnterContest, UnsafeApiAllowed)

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
        contest = get_object_or_404(Contest, id=contest_id)
        problem_instance = get_object_or_404(
            ProblemInstance, contest=contest, problem__short_name=problem_short_name
        )

        user_problem_submits = (
            Submission.objects.filter(
                user=request.user, problem_instance=problem_instance
            )
            .order_by('-date')
            .select_related(
                'problem_instance',
                'problem_instance__contest',
                'problem_instance__round',
                'problem_instance__problem',
            )
        )
        last_20_submits = user_problem_submits[:20]
        submissions = [submission_template_context(request, s) for s in last_20_submits]
        submissions_data = {'submissions': []}
        for submission_entry in submissions:
            score = (
                submission_entry['submission'].score
                if submission_entry['can_see_score']
                else None
            )
            submission_status = (
                submission_entry['submission'].status
                if submission_entry['can_see_status']
                else None
            )
            submissions_data['submissions'].append(
                {
                    'id': submission_entry['submission'].id,
                    'date': submission_entry['submission'].date,
                    'score': score.to_int() if score else None,
                    'status': submission_status,
                }
            )
        submissions_data['is_truncated_to_20'] = len(user_problem_submits) > 20
        return Response(submissions_data, status=status.HTTP_200_OK)


class GetUserProblemSubmissionCode(views.APIView):
    permission_classes = (IsAuthenticated, CanEnterContest, UnsafeApiAllowed)

    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='contest_id',
                title="Name of the contest",
                description="Id of the contest to which the problem you want to "
                "query belongs. You can find this id after /c/ in urls "
                "when using SIO 2 web interface.",
            ),
            make_path_coreapi_schema(
                name='submission_id',
                title="Submission id",
                description="You can query submission ID list at problem_submission_list endpoint.",
            ),
        ]
    )

    def get(self, request, contest_id, submission_id):
        # Make sure user made this submission, not somebody else.
        submission = get_object_or_404(ProgramSubmission, id=submission_id)
        if submission.user != request.user:
            raise Http404("Submission not found.")

        source_file = get_submission_source_file_or_error(request, int(submission_id))
        raw_source, decode_error = decode_str(source_file.read())
        if decode_error:
            return Response(
                'Error during decoding the source code.',
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"lang": source_file.name.split('.')[-1], "code": raw_source},
            status=status.HTTP_200_OK,
        )


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


# This is a base class for submitting a solution for contests and problemsets.
# It lacks get_problem_instance, as it's specific to problem source.
class SubmitSolutionView(views.APIView):
    permission_classes = (IsAuthenticated, CanEnterContest, UnsafeApiAllowed)

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
