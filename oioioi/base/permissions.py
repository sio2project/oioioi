# coding: utf-8

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
import functools

def enforce_condition(condition):
    """Decorator for views that checks that the request passes the given
       ``condition``.

       If the condition returns ``False`` and the user is not authenticated, a
       redirect to the login page is issued, otherwise :exc:`PermissionDenied`
       is raised.

       :param condition: condition to check
       :type condition: function request → bool
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if condition(request):
                return view_func(request, *args, **kwargs)
            if not request.user.is_authenticated():
                return redirect_to_login(request.path)
            else:
                raise PermissionDenied
        return _wrapped_view
    return decorator

def not_anonymous(request):
    return request.user.is_authenticated()
