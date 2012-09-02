from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from oioioi.problems.models import Problem
import functools

def problem_admin_permission_required(fn):
    @functools.wraps(fn)
    def wrapped(request, *args, **kwargs):
        problem_id = kwargs['problem_id']
        problem = get_object_or_404(Problem, id=problem_id)
        if not request.user.has_perm('problems.problem_admin', problem):
            raise PermissionDenied(_("Problem administration privileges "
                "required"))
        return fn(request, *args, **kwargs)
    return wrapped
