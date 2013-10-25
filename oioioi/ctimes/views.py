from datetime import timedelta
import json
import time
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from oioioi.contests.models import Round


def ctimes_response_dict(request):
    now = request.timestamp
    contest = request.contest
    if contest is None:
        return {
            'status': 'NO_CONTEST'
        }
    ccontroller = contest.controller
    rtimes = [ccontroller.get_round_times(request, round)
              for round in Round.objects.filter(contest=request.contest)]
    rtimes = [rtime for rtime in rtimes
              if now <= rtime.get_end() + timedelta(minutes=30)]

    def ctimes_sort_key(round_time):
        return (not round_time.get_start() <= now <= round_time.get_end(),
                not round_time.get_start() - timedelta(minutes=5) <= now,
                round_time.get_end())

    try:
        rtime = min(rtimes, key=ctimes_sort_key)
        date_format = '%Y-%m-%d %H:%M:%S'
        to_seconds = lambda date: int(time.mktime(date.timetuple()))
        start = timezone.localtime(rtime.get_start())
        end = timezone.localtime(rtime.get_end())
        return {
            'status': 'OK',
            'start': start.strftime(date_format),
            'start_sec': to_seconds(start),
            'end': end.strftime(date_format),
            'end_sec': to_seconds(end)
        }
    except ValueError:
        return {
            'status': 'NO_ROUND',
        }


def ctimes_view(request):
    if not request.user.is_authenticated():
        raise PermissionDenied
    response_dict = ctimes_response_dict(request)
    return HttpResponse(json.dumps(response_dict),
            content_type='application/json')
