from django.http import Http404
from django.shortcuts import get_object_or_404
from oioioi.base.utils.api import make_path_coreapi_schema
from oioioi.contests.forms import SubmissionFormForProblemInstance
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.contests.serializers import SubmissionSerializer
from oioioi.contests.utils import can_enter_contest
from oioioi.problems.models import Problem
from rest_framework import permissions, status, views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema


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
        response_data = {
            'problem_id': problem_instance.problem_id,
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
