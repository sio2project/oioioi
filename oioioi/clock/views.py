from django.http import HttpResponse
import json
import time

def get_time_view(request):
    """Returns the current time as JSON.

       Returns a dictionary with a single key ``time`` being the number
       of seconds elapsed since the epoch.
    """
    response = dict(time=time.mktime(request.timestamp.timetuple()))
    return HttpResponse(json.dumps(response), content_type='application/json')
