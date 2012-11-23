from django.http import HttpResponse
from django.utils import timezone
import json
import time

def get_times_view(request):
    """Returns the current rounds times as JSON.

       Returns a dictionary with keys:
       ``time``: the number of seconds elapsed since the epoch
       ``round_start_date``: the number of seconds between the epoch
       and the start of the current round if any exists; otherwise 0
       ``round_end_date`` the number of seconds between the epoch
       and the end of the current round if any exists; otherwise 0
    """
    timestamp = getattr(request, 'timestamp', None)
    contest = getattr(request, 'contest', None)
    response = dict(time=0, round_start_date=0, round_end_date=0)

    if timestamp:
        response['time'] = time.mktime((timezone \
             .localtime(timestamp)).timetuple())

    if (contest and timestamp):
        next_rounds = contest.round_set.filter(end_date__gt=timestamp) \
            .order_by('start_date')
        current_rounds = next_rounds.filter(start_date__lt=timestamp) \
            .order_by('end_date')
    else:
        next_rounds = 0
        current_rounds = 0

    if current_rounds:
        response['round_start_date'] = time.mktime((timezone \
            .localtime(current_rounds[0].start_date)).timetuple())
        response['round_end_date'] = time.mktime((timezone \
            .localtime(current_rounds[0].end_date)).timetuple())
    elif next_rounds:
        response['round_start_date'] = time.mktime((timezone \
            .localtime(next_rounds[0].start_date)).timetuple())

    return HttpResponse(json.dumps(response), content_type='application/json')
