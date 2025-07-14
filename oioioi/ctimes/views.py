import time
from datetime import timedelta  # pylint: disable=E0611

from django.utils import timezone

from oioioi.base.utils import allow_cross_origin, jsonify
from oioioi.contests.models import Round


@allow_cross_origin
@jsonify
def ctimes_view(request):
    now = request.timestamp
    contest = request.contest
    if contest is None:
        return {"status": "NO_CONTEST"}

    def end_le(a, b):
        """Compare round ends. None means "round does not end",
        so it ends not earlier than any other."""
        return True if b is None else b >= a

    ccontroller = contest.controller
    rounds = [(ccontroller.get_round_times(request, round), round) for round in Round.objects.filter(contest=request.contest)]
    rounds = [(rtime, round) for (rtime, round) in rounds if end_le(now - timedelta(minutes=30), rtime.get_end())]

    def ctimes_sort_key(round_time):
        return (
            not (round_time.get_start() <= now and end_le(now, round_time.get_end())),
            not round_time.get_start() - timedelta(minutes=5) <= now,
            round_time.get_end(),
        )

    try:
        (rtime, round) = min(rounds, key=lambda x: ctimes_sort_key(x[0]))
        date_format = "%Y-%m-%d %H:%M:%S"
        start = timezone.localtime(rtime.get_start())
        if rtime.get_end() is None:
            end = None
        else:
            end = timezone.localtime(rtime.get_end())

        def to_seconds(date):
            return None if date is None else int(time.mktime(date.timetuple()))

        def format_date(date):
            return None if date is None else date.strftime(date_format)

        return {
            "status": "OK",
            "round_name": round.name,
            "start": format_date(start),
            "start_sec": to_seconds(start),
            "end": format_date(end),
            "end_sec": to_seconds(end),
        }
    except ValueError:
        return {
            "status": "NO_ROUND",
        }
