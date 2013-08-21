from django.contrib.auth import BACKEND_SESSION_KEY
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.http import HttpResponseNotAllowed
from django.template import RequestContext
from django.template.loader import render_to_string


class TimestampingMiddleware(object):
    """Middleware which adds an attribute ``timestamp`` to each ``request``
       object, representing the request time as :class:`datetime.datetime`
       instance.

       It should be placed as close to the begging of the list of middlewares
       as possible.
    """

    def process_request(self, request):
        if 'admin_time' in request.session:
            request.timestamp = request.session['admin_time']
        else:
            request.timestamp = timezone.now()


class HttpResponseNotAllowedMiddleware(object):
    def process_response(self, request, response):
        if isinstance(response, HttpResponseNotAllowed):
            response.content = render_to_string("405.html",
                    context_instance=RequestContext(request,
                        {'allowed': response['Allow']}))
        return response


class AnnotateUserBackendMiddleware(object):
    """Middleware annotating user object with path of authentication backend."""

    def process_request(self, request):
        # Newly authenticated user objects are annotated with succeeded backend,
        # but it's not restored in AuthenticationMiddleware.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The annotating user with backend middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the AnnotateUserBackendMiddleware class.")

        if BACKEND_SESSION_KEY in request.session:
            # Barbarously discard request.user laziness.
            request.user.backend = request.session[BACKEND_SESSION_KEY]
