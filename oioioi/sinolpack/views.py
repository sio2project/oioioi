from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from oioioi.filetracker.utils import stream_file
from oioioi.sinolpack.models import ExtraFile


def download_extra_file_view(request, file_id):
    file = get_object_or_404(ExtraFile, id=file_id)
    if not request.user.has_perm('problems.problem_admin', file.problem):
        raise PermissionDenied
    return stream_file(file.file)
