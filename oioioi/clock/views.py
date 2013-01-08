from django.http import HttpResponse
from django.utils import timezone
from oioioi.contests.models import Round
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
    user = getattr(request, 'user', None)

    next_rounds_times = None
    current_rounds_times = None

    if timestamp:
        response['time'] = time.mktime((timezone \
             .localtime(timestamp)).timetuple())
        if contest:
            rounds_times = [contest.controller \
                    .get_round_times(request, round) \
                    for round in Round.objects.filter(contest=contest)]
            next_rounds_times = filter(lambda rt: rt.is_future(timestamp),
                    rounds_times)
            next_rounds_times.sort(key=lambda rt: rt.get_start())
            current_rounds_times = filter(lambda rt: rt.get_end(),
                    filter(lambda rt: rt.is_active(timestamp), rounds_times))
            current_rounds_times.sort(key=lambda rt: rt.get_end())

    if current_rounds_times:
        response['round_start_date'] = time.mktime((timezone \
            .localtime(current_rounds_times[0].get_start())).timetuple())
        response['round_end_date'] = time.mktime((timezone \
            .localtime(current_rounds_times[0].get_end())).timetuple())
    elif next_rounds_times:
        response['round_start_date'] = time.mktime((timezone \
            .localtime(next_rounds_times[0].get_start())).timetuple())

    return HttpResponse(json.dumps(response), content_type='application/json')
