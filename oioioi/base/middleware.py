from django.utils.timezone import get_current_timezone
import datetime
from django.shortcuts import render_to_response
from django.conf import settings
import os.path

class TimestampingMiddleware(object):
    """Middleware which adds an attribute ``timestamp`` to each ``request``
       object, representing the request time as :cls:`datetime.datetime`
       instance.

       It should be placed as close to the begging of the list of middlewares
       as possible.
    """

    def process_request(self, request):
        request.timestamp = datetime.datetime.now(get_current_timezone())

class FriendlyWarningsMiddleware(object):
    def process_request(self, request):
        import sys
        RUNNING_DEVSERVER = (len(sys.argv) > 1 and sys.argv[1] == 'runserver')

        if RUNNING_DEVSERVER or settings.SUPPRESS_FRIENDLY_WARNINGS:
            return None
        else:
            db_name =  settings.DATABASES['default']['NAME']
            db_engine = settings.DATABASES['default']['ENGINE']
            context = dict()
            if 'sqlite' in db_engine:
                context['sqlite'] = True
                context['sqlite_relative_path'] = not os.path.isabs(db_name)

            if settings.USE_UNSAFE_EXEC:
                context['use_unsafe_exec'] = True
            if settings.USE_LOCAL_COMPILERS:
                context['use_local_compilers'] = True
            if settings.DEBUG:
                context['debug'] = True

            if len(context) != 0:
                return render_to_response('friendly-warnings.html', context)
