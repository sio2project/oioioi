# -*- coding: utf-8 -*-
from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def enforce_condition(condition, redirect_to=None, view=None):
    """
       :param condition: condition to check
       :type condition: function request → bool
       :param redirect_to: url to redirect if condition returns false
       :type redirect_to: string
       :param view: view to display if condition returns false
       :type view: string
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if condition(request):
                return view_func(request, *args, **kwargs)
            if not request.user.is_authenticated():
                return redirect_to_login(request.path)
            if redirect_to:
                return redirect(redirect_to)
            if view:
                return view(request)
            else:
                raise PermissionDenied
        return _wrapped_view
    return decorator

def not_anonymous(request):
    return request.user.is_authenticated()

