from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema
from rest_framework import permissions, serializers, views
from oioioi.base.utils.api import make_path_coreapi_schema
from oioioi.contests.models import ProblemInstance
from oioioi.contests.forms import SubmissionFormForProblemInstance
from oioioi.problems.models import Problem


class CanEnterContest(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_enter_contest(request)


class SubmissionSerializer(serializers.Serializer):
    file = serializers.FileField(help_text='File with the problem solution. '
                                           'It should have name which allows '
                                           'programming language recognition.')
    kind = serializers.CharField(required=False,
                                 help_text='It is an advanced parameter determining '
                                           'submission kind. It usually defaults '
                                           'to normal and you should not '
                                           'set it manually.')
    problem_instance = None

    def __init__(self, pi, *args, **kwargs):
        if pi is not None:
            self.problem_instance_id = serializers.HiddenField(default=pi.pk)
        self.problem_instance = pi

        super(SubmissionSerializer, self).__init__(*args, **kwargs)

    def validate(self, data):
        for field in SubmissionSerializer.Meta.fields:
            if data.get(field, None) is None and field in self.__dict__:
                data[field] = self.__dict__[field].default
        return data

    class Meta:
        fields = ('file', 'kind', 'problem_instance_id')


class SubmitSolution(views.APIView):
    serializer_class = SubmissionSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    def get_serializer(self):
        return self.serializer_class(None)

    def get_problem_instance(self, **kwargs):
        raise NotImplemented

    def post(self, request, **kwargs):
        """This endpoint allows you to submit solution for selected problem. """
        pi = self.get_problem_instance(**kwargs)
        serializer = SubmissionSerializer(pi=pi, data=request.data)

        serializer.is_valid(raise_exception=True)
        form = SubmissionFormForProblemInstance(request,
                                                serializer.problem_instance,
                                                serializer.validated_data,
                                                request.FILES)
        if not form.is_valid():
            return Response(form.errors, status=400)

        submission = serializer.problem_instance.controller.create_submission(
            request, form.cleaned_data['problem_instance'], form.cleaned_data)

        return Response(submission.id)


class SubmitContestSolution(SubmitSolution):
    permission_classes = (IsAuthenticated, CanEnterContest,)
    schema = AutoSchema([
        make_path_coreapi_schema(
            name='contest_name', title='Contest name',
            description='Name of the contest to which you want to submit '
                        'solution. You can find it after /c/ in urls '
                        'when using SIO 2 web interface.'),
        make_path_coreapi_schema(
            name='problem_short_name', title='Problem short name',
            description='Short name of the problem to which you want to submit '
                        'solution. You can find it for example in first column '
                        'of problem list when using SIO 2 web interface.'),
    ])

    def get_problem_instance(self, contest_name, problem_short_name):
        return get_object_or_404(ProblemInstance, contest=contest_name,
                                 short_name=problem_short_name)


class SubmitProblemsetSolution(SubmitSolution):
    schema = AutoSchema([
        make_path_coreapi_schema(
            name='problem_site_key', title='Contest name',
            description='This is unique key for the problem in problemset. '
                        'You can find it after /problemset/problem/ in url of '
                        'any site related to the problem when using SIO 2 web '
                        'interface.'),
    ])

    def get_problem_instance(self, problem_site_key):
        problem = get_object_or_404(Problem, problemsite__url_key=problem_site_key)
        pi = problem.main_problem_instance
        if not pi:
            raise Http404
        return pi
