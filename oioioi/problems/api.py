from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from oioioi.base.utils.api import make_path_coreapi_schema
from oioioi.contests.models import Contest
from oioioi.contests.utils import can_admin_contest
from oioioi.problems.forms import PackageUploadForm
from oioioi.problems.models import Problem, ProblemPackage
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.problems.serializers import (
    PackageReuploadSerializer,
    PackageUploadSerializer,
)
from oioioi.problems.utils import can_admin_problem
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.schemas import AutoSchema
from rest_framework.views import APIView


def _check_permissions(request, contest=None, existing_problem=None):
    if not request.user.has_perm('problems.problems_db_admin'):
        if contest and (not can_admin_contest(request.user, contest)):
            return False
    if existing_problem:
        if not can_admin_problem(request, existing_problem):
            return False
    return True


class PackageUploadQueryView(APIView):
    """Endpoint that given package_id returns package_status.
    Possible values for the package_status are:
    - "OK": if the package was successfully uploaded (if so, the problem_id is returned,
    if one is available),
    - "ERR": if the package upload failed (if so, info describing an error is returned,
    if one is available),
    - "?": if the package upload is pending.
    """

    permission_classes = (IsAuthenticated,)
    schema = AutoSchema(
        [
            make_path_coreapi_schema(
                name='package_id',
                title="Package id",
                description="Id of the package whose status you can get.",
            ),
        ]
    )

    @staticmethod
    def check_permissions(request, contest=None, existing_problem=None):
        return _check_permissions(
            request, contest=contest, existing_problem=existing_problem
        )

    def get(self, request, package_id):
        package = get_object_or_404(ProblemPackage, id=package_id)
        if not self.check_permissions(request, package.contest, package.problem):
            return Response(
                {'message': _("Permission denied.")}, status=status.HTTP_403_FORBIDDEN
            )

        response = {'package_status': package.status}
        if response['package_status'] == 'OK':
            if package.problem_id is not None:
                response['problem_id'] = package.problem_id
        elif response['package_status'] == 'ERR':
            if package.info is not None:
                response['info'] = package.info

        return Response(response, status=status.HTTP_200_OK)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class BasePackageUploadView(APIView):
    parser_class = (MultiPartParser,)
    permission_classes = (IsAuthenticated,)
    serializer_class = None
    form_class = PackageUploadForm

    @staticmethod
    def check_permissions(request, contest=None, existing_problem=None):
        return _check_permissions(
            request, contest=contest, existing_problem=existing_problem
        )

    @staticmethod
    def prepare_data(dictionary):
        raise NotImplementedError

    @staticmethod
    def submit_upload_form(form, request, contest):
        return UploadedPackageSource().handle_form(form, request, contest)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = self.prepare_data(serializer.validated_data)

            contest = data.get('contest')
            existing_problem = data.get('existing_problem')
            form_data = data.get('form_data')

            if not self.check_permissions(request, contest, existing_problem):
                return Response(
                    {'message': _("Permission denied.")},
                    status=status.HTTP_403_FORBIDDEN,
                )

            form = self.form_class(contest, existing_problem, form_data, request.FILES)
            if form_data.get('round_id'):
                form.data['round_id'] = form_data['round_id']

            package_id = self.submit_upload_form(form, request, contest)

            if package_id is not None:
                return Response(
                    {'package_id': package_id}, status=status.HTTP_201_CREATED
                )
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PackageUploadView(BasePackageUploadView):
    """Endpoint allowing for uploading problem packages.
    Each uploaded problem has to be bound to some round and contest.
    """

    serializer_class = PackageUploadSerializer

    @staticmethod
    def prepare_data(dictionary):
        contest_id = dictionary['contest_id']
        round_name = dictionary['round_name']

        contest = Contest.objects.filter(id=contest_id).first()
        existing_problem = None

        form_data = {
            'contest_id': contest.id,
            'round_id': contest.round_set.filter(name=round_name).first().id,
        }

        data = {
            'contest': contest,
            'existing_problem': existing_problem,
            'form_data': form_data,
        }

        return data


class PackageReuploadView(BasePackageUploadView):
    """Endpoint allowing for reuploading problem packages.
    Substitutes package file corresponding to specified problem with uploaded package.
    """

    serializer_class = PackageReuploadSerializer

    @staticmethod
    def prepare_data(dictionary):
        contest = None
        existing_problem = get_object_or_404(Problem, id=dictionary['problem_id'])

        form_data = {}

        data = {
            'contest': contest,
            'existing_problem': existing_problem,
            'form_data': form_data,
        }

        return data
