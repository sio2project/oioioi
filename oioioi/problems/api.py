from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator

from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from oioioi.problems.models import Problem, ProblemPackage
from oioioi.problems.serializers import (PackageReuploadSerializer,
                                         PackageUploadSerializer,
                                         PackageUploadQuerySerializer)
from oioioi.problems.forms import PackageUploadForm
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.problems.utils import can_admin_problem

from oioioi.contests.models import Contest
from oioioi.contests.utils import can_admin_contest


class PackageUploadQueryView(APIView):
    """ Endpoint that given package_id returns package_status.
    Possible values for package_status are:
    "OK" if package was succesfully uploaded (if so, the problem_id is returned if one is available),
    "ERR" if package upload failed (if so, info describing error is returned if one is available),
    "?" if package upload is pending."""
    parser_class = (MultiPartParser,)
    permission_classes = (IsAuthenticated,)
    serializer_class = PackageUploadQuerySerializer

    def get_serializer(self):
        return self.serializer_class(None)

    @staticmethod
    def check_permissions(request):
        return request.user.has_perm('problems.problems_db_admin')

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            package_id = data['package_id']

            if not self.check_permissions(request):
                return Response({'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

            package = get_object_or_404(ProblemPackage, id=package_id)
            answer = {'package_status': package.status}

            if answer['package_status'] == 'OK':
                if package.problem is not None:
                    answer['problem_id'] = package.problem.id

            if answer['package_status'] == 'ERR':
                if package.info is not None:
                    answer['info'] = package.info

            return Response(answer, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class BasePackageUploadView(APIView):
    parser_class = (MultiPartParser,)
    permission_classes = (IsAuthenticated,)
    serializer_class = None
    form_class = PackageUploadForm

    def get_serializer(self):
        return self.serializer_class(None)

    @staticmethod
    def check_permissions(request, contest=None, existing_problem=None):
        if not request.user.has_perm('problems.problems_db_admin'):
            if contest and (not can_admin_contest(request.user, contest)):
                return False
        if (existing_problem):
            if not can_admin_problem(request, existing_problem):
                return False
        return True

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
                return Response({'message': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

            form = self.form_class(contest, existing_problem, form_data, request.FILES)
            if (form_data.get('round_id')):
                form.data['round_id'] = form_data['round_id']

            package_id = self.submit_upload_form(form, request, contest)

            if package_id is not None:
                return Response({'package_id': package_id}, status=status.HTTP_201_CREATED)
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PackageUploadView(BasePackageUploadView):
    """ Endpoint allowing for uploading problem packages.
    Each uploaded problem has to be bound to some round and contest."""
    serializer_class = PackageUploadSerializer

    @staticmethod
    def prepare_data(dictionary):
        contest_id = dictionary['contest_id']
        round_name = dictionary['round_name']

        contest = Contest.objects.filter(id=contest_id).first()
        existing_problem = None

        form_data = {'contest_id': contest.id,
                     'round_id': contest.round_set.filter(name=round_name).first().id}

        data = {'contest': contest,
                'existing_problem': existing_problem,
                'form_data': form_data}

        return data


class PackageReuploadView(BasePackageUploadView):
    """ Endpoint allowing for reuploading problem packages.
        Substitutes package file corresponding to specified problem with uploaded package."""
    serializer_class = PackageReuploadSerializer

    @staticmethod
    def prepare_data(dictionary):
        contest = None
        existing_problem = get_object_or_404(Problem, id=dictionary['problem_id'])

        form_data = {}

        data = {'contest': contest,
                'existing_problem': existing_problem,
                'form_data': form_data}

        return data
