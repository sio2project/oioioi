import os
import tempfile

from django.http import FileResponse
from django.template.response import TemplateResponse

from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists, is_contest_admin
from oioioi.exportszu.forms import ExportSubmissionsForm
from oioioi.exportszu.utils import (
    SubmissionsWithUserDataCollector,
    build_submissions_archive,
)


@enforce_condition(contest_exists & is_contest_admin)
def export_submissions_view(request):
    if request.method == 'POST':
        form = ExportSubmissionsForm(request, request.POST)
        if form.is_valid():
            round = form.cleaned_data['round']
            only_final = form.cleaned_data['only_final']
            collector = SubmissionsWithUserDataCollector(
                request.contest, round=round, only_final=only_final
            )
            # TemporaryFile promises removal of the file when it is closed.
            # Note that we cannot use with, because we want to keep it beyond
            # this function call.
            tmp_file = tempfile.TemporaryFile()
            build_submissions_archive(tmp_file, collector)
            # We send a large file with django. Usually it isn't a good idea,
            # but letting the web server do it leads to problems with when to
            # delete this file and from where.
            tmp_file.seek(0, os.SEEK_SET)  # go to the beginning of the file
            response = FileResponse(tmp_file)
            response['Content-Type'] = 'application/gzip'
            response['Content-Disposition'] = (
                'attachment; filename="%s.tgz"' % request.contest.id
            )
            return response
    else:
        form = ExportSubmissionsForm(request)
    return TemplateResponse(
        request, 'exportszu/export_submissions.html', {'form': form}
    )
