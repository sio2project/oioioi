from dateutil.parser import parse as parse_date
from django.contrib import messages
from django.contrib.auth import BACKEND_SESSION_KEY
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotAllowed
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.user import has_valid_username, has_valid_name
from oioioi.base.utils.middleware import was_response_generated_by_exception
from oioioi.su.utils import is_under_su


class TimestampingMiddleware(object):
    """Middleware which adds an attribute ``timestamp`` to each ``request``
       object, representing the request time as :class:`datetime.datetime`
       instance.

       It should be placed as close to the begging of the list of middlewares
       as possible.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)

        return self.get_response(request)

    def _process_request(self, request):
        if 'admin_time' in request.session:
            request.timestamp = parse_date(request.session['admin_time'])
        else:
            request.timestamp = timezone.now()


class HttpResponseNotAllowedMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return self._process_response(request, response)

    def _process_response(self, request, response):
        if isinstance(response, HttpResponseNotAllowed):
            response.content = render_to_string("405.html",
                    request=request, context={'allowed': response['Allow']})
        return response


class AnnotateUserBackendMiddleware(object):
    """Middleware annotating user object with path of authentication
       backend.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)

        return self.get_response(request)

    def _process_request(self, request):
        # Newly authenticated user objects are annotated with succeeded
        # backend, but it's not restored in AuthenticationMiddleware.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The annotating user with backend middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the AnnotateUserBackendMiddleware class.")

        if BACKEND_SESSION_KEY in request.session:
            # Barbarously discard request.user laziness.
            request.user.backend = request.session[BACKEND_SESSION_KEY]


class UserInfoInErrorMessage(object):
    """Add username and email of a user who caused an exception
       to error message."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if was_response_generated_by_exception(response):
            self.process_exception(request, None)

        return response

    def process_exception(self, request, exception):
        # pylint: disable=broad-except
        try:
            if not hasattr(request, 'user'):
                return

            # This is because is_authenticated is a CallableBool not bool until Django 2.0,
            # so its str is not True/False as expected.
            request.META['IS_AUTHENTICATED'] = \
                str(bool(request.user.is_authenticated))
            request.META['IS_UNDER_SU'] = str(is_under_su(request))

            if request.user.is_authenticated:
                request.META['USERNAME'] = str(request.user.username)
                request.META['USER_EMAIL'] = str(request.user.email)

            if is_under_su(request):
                request.META['REAL_USERNAME'] = str(request.real_user.username)
                request.META['REAL_USER_EMAIL'] = str(request.real_user.email)

        except Exception:
            pass


class CheckLoginMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)
        return self.get_response(request)

    def _process_request(self, request):
        valid_username = has_valid_username(request.user)
        valid_name = has_valid_name(request.user)
        if valid_name and valid_username:
            return

        storage = messages.get_messages(request)
        check_login_message = \
            _("Your login - %(login)s - contains forbidden characters. ") \
            % {'login': request.user.username}

        check_name_message = \
            _("Your name - %(name)s %(surname)s - "
              "contains forbidden characters. ") \
            % {'name': request.user.first_name,
               'surname': request.user.last_name}

        message_appendix = \
            _("Please click <a href='%(link)s'>here</a> to change it. "
              "It will take only a while.") \
            % {'link': reverse('edit_profile')}

        final_message = ""
        if not valid_username:
            final_message += check_login_message
        if not valid_name:
            final_message += check_name_message
        final_message += message_appendix

        # https://docs.djangoproject.com/en/dev/ref/contrib/messages/#expiration-of-messages
        all_messages = [s.message for s in storage]
        storage.used = False

        if final_message in all_messages:
            return
        messages.add_message(request, messages.INFO,
                             mark_safe(final_message))
