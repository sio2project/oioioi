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

    def get_end(rtime):
        """Get round end for comparisons. None means "round does not end",
        so in comparisons it shouldn't be earlier than any other."""
        return rtime.get_key_for_comparison()[1]

    ccontroller = contest.controller
    rounds = [(ccontroller.get_round_times(request, round), round) for round in Round.objects.filter(contest=request.contest)]

    end_cutoff = now - timedelta(minutes=5)
    rounds = [(rtime, round) for (rtime, round) in rounds if not rtime.is_past(end_cutoff)]

    def ctimes_sort_key(round_time):
        # See README.rst for an explanation of the ordering.
        if round_time.is_active(now):
            return (0, get_end(round_time))
        if round_time.is_past(now):
            # Of past rounds, we want the one that ended last.
            return (2, now - get_end(round_time))
        starts_soon = not round_time.is_future(now + timedelta(minutes=5))
        return (1 if starts_soon else 3, round_time.get_start())

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
