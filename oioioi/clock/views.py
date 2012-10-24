from django.http import HttpResponse
from django.utils import timezone
import json
import time

def get_time_view(request):
    """Returns the current time as JSON.

       Returns a dictionary with a single key ``time`` being the number
       of seconds elapsed since the epoch.
    """
    localtimestamp = timezone.localtime(request.timestamp)
    response = dict(time=time.mktime(localtimestamp.timetuple()))
    return HttpResponse(json.dumps(response), content_type='application/json')
