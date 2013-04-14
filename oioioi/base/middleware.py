from django.utils import timezone
from django.http import HttpResponseNotAllowed
from django.template import RequestContext
from django.template.loader import render_to_string

class TimestampingMiddleware(object):
    """Middleware which adds an attribute ``timestamp`` to each ``request``
       object, representing the request time as :cls:`datetime.datetime`
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
