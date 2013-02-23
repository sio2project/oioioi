# coding: utf-8

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
import functools

class AccessDenied(object):
    """A ``False``-like class with additional response to use as the access
       denied message.
    """

    def __init__(self, response=None):
        self.response = response

    def __nonzero__(self):
        return False

def enforce_condition(condition):
    """Decorator for views that checks that the request passes the given
       ``condition``.

       If the condition returns ``False`` and the user is not authenticated, a
       redirect to the login page is issued, otherwise :exc:`PermissionDenied`
       is raised.

       If the condition returns an instance of :class:`AccessDenied` with a
       specific response to use, this response is used instead of calling the
       decorated view.

       :param condition: condition to check
       :type condition: function request → bool
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            decision = condition(request)
            if isinstance(decision, AccessDenied) and decision.response:
                return decision.response
            if decision:
                return view_func(request, *args, **kwargs)
            if not request.user.is_authenticated() and not request.is_ajax():
                return redirect_to_login(request.path)
            else:
                raise PermissionDenied
        return _wrapped_view
    return decorator

def not_anonymous(request):
    return request.user.is_authenticated()
