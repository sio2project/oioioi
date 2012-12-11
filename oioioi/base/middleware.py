from django.utils import timezone

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
