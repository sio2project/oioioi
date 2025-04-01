# coding: utf-8
import functools

from django.contrib.auth.views import LogoutView, redirect_to_login
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.contrib.auth import logout

from oioioi.base.utils import is_ajax


class AccessDenied(object):
    """A ``False``-like class with additional response to use as the access
    denied message.
    """

    def __init__(self, response=None):
        self.response = response

    def __nonzero__(self):
        return False


class Condition(object):
    r"""Class representing a condition (a function which returns a boolean
    based on its arguments) intended for use with views and menu items.

    Technically, an instance of this class is a callable object wrapping
    a function.

    Additionally, it implements basic logical operators: AND (&), OR (|),
    and (~) -- a logical negation.

    :param condition: the function to be wrapped
    :type condition: fun: \*args, \*\*kwargs → bool
    """

    def __init__(self, condition, *args, **kwargs):
        super(Condition, self).__init__(*args, **kwargs)
        self.condition = condition

    def __call__(self, *args, **kwargs):
        return self.condition(*args, **kwargs)

    def __or__(self, other):
        if not isinstance(other, Condition):
            return NotImplemented
        condition_or = lambda *args, **kwargs: self(*args, **kwargs) or other(
            *args, **kwargs
        )
        return Condition(condition_or)

    def __and__(self, other):
        if not isinstance(other, Condition):
            return NotImplemented
        condition_and = lambda *args, **kwargs: self(*args, **kwargs) and other(
            *args, **kwargs
        )
        return Condition(condition_and)

    def __invert__(self):
        condition_inverted = lambda *args, **kwargs: not self(*args, **kwargs)
        return Condition(condition_inverted)


class RequestBasedCondition(Condition):
    """Subclass of the :class:`Condition` class.

    It is a special condition class representing a condition which takes
    request as its only argument.

    It allows the usage of :func:`oioioi.base.utils.request_cached`.
    """

    def __call__(self, request, *args, **kwargs):
        return self.condition(request)


def make_condition(condition_class=Condition):
    """Decorator which transforms a function into an instance of a given
    ``condition_class`` (subclass of :class:`~Condition`).
    """
    assert issubclass(condition_class, Condition)

    def wrap_condition(func):
        condition = condition_class(func)
        for attr in ('__name__', '__module__', '__doc__'):
            setattr(condition, attr, getattr(func, attr))
        condition.__dict__.update(func.__dict__)
        return condition

    return wrap_condition


#: Shortcut for ``make_condition(RequestBasedCondition)``.
#: See example usage below.
make_request_condition = make_condition(RequestBasedCondition)


def enforce_condition(condition, template=None, login_redirect=True):
    """Decorator for views that checks that the request passes the given
    ``condition``.

    ``condition`` must be an instance of :class:`Condition`.

    If the condition returns ``False`` and ``template`` is not ``None``,
    a suitable :class:`TemplateResponse` is returned.

    If ``template`` is ``None`` and the user is not authenticated and the
    ``login_redirect`` flag is set to ``True``, a redirect to the login
    page is issued, otherwise :exc:`PermissionDenied` is raised.

    If the condition returns an instance of :class:`AccessDenied` with a
    specific response to use, this response is used instead of calling the
    decorated view.

    :param condition: condition to check
    :type condition: :class:`Condition`
    :param template: template name to return when ``condition`` fails
    :type template: basestring
    """
    assert isinstance(condition, Condition), (
        'condition passed to'
        ' enforce_condition must be an instance of the Condition class or'
        ' its subclass'
    )

    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            decision = condition(request, *args, **kwargs)
            if isinstance(decision, AccessDenied) and decision.response:
                return decision.response
            if decision:
                return view_func(request, *args, **kwargs)
            if template is not None:
                return TemplateResponse(request, template)
            elif (
                not request.user.is_authenticated
                and not is_ajax(request)
                and login_redirect
            ):
                return redirect_to_login(request.path)
            else:
                raise PermissionDenied

        old_condition = getattr(view_func, 'condition', None)
        if old_condition is None:
            new_condition = condition
        else:
            new_condition = condition & old_condition
        _wrapped_view.condition = new_condition
        return _wrapped_view

    return decorator


@make_request_condition
def not_anonymous(request):
    """
    Checks if user is logged in and if his account is active.
    Logs out inactive users, effectively blocking
    them from performing actions.

    :param request:
    :return:
    """
    if request.user.is_authenticated:
        if request.user.is_active:
            return True
        else:
            logout(request)
            return False
    else:
        return False


@make_request_condition
def is_superuser(request):
    return request.user.is_superuser
