from django.http import HttpResponse, Http404
from django.utils import timezone
from oioioi.contests.models import Round
from django.shortcuts import redirect
from datetime import datetime
import pytz
import re
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
       ``is_admin_time_set``: ``True`` if admin changes the time
    """
    timestamp = getattr(request, 'timestamp', None)
    contest = getattr(request, 'contest', None)
    response = dict(time=0, round_start_date=0, round_end_date=0,
        is_admin=False, is_admin_time_set=False)
    user = getattr(request, 'user', None)

    if 'admin_time' in request.session:
        response['is_admin_time_set'] = True
    if user and user.is_superuser:
        response['is_admin'] = True

    next_rounds_times = None
    current_rounds_times = None

    if timestamp:
        response['time'] = time.mktime((timezone
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

def admin_time(request, path):
    if not path.startswith('/'):
        path = '/' + path
    if request.method == 'POST':
        if 'reset-button' in request.POST:
            if 'admin_time' in request.session:
                del request.session['admin_time']
            return redirect(path)
        elif request.user.is_superuser:
            admin_time = re.findall(r'\d+', request.POST['admin-time'])
            admin_time = map(int, admin_time)
            try:
                admin_time = datetime(*admin_time)
            except (ValueError, TypeError, OverflowError):
                return redirect(path)
            if admin_time.year >= 1900:
                request.session['admin_time'] = \
                    timezone.localtime(timezone.now()). \
                    tzinfo.localize(admin_time).astimezone(pytz.utc)
            return redirect(path)
    raise Http404
