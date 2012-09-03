from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from oioioi.problems.models import ProblemStatement
from oioioi.filetracker.utils import stream_file

def show_statement_view(request, statement_id):
    statement = get_object_or_404(ProblemStatement, id=statement_id)
    if not request.user.has_perm('problems.problem_admin', statement.problem):
        raise PermissionDenied
    return stream_file(statement.content)
