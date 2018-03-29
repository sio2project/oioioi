from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from oioioi.filetracker.utils import stream_file
from oioioi.problems.utils import can_admin_problem
from oioioi.sinolpack.models import ExtraFile


def download_extra_file_view(request, file_id):
    file = get_object_or_404(ExtraFile, id=file_id)
    if not can_admin_problem(request, file.problem):
        raise PermissionDenied
    return stream_file(file.file)
