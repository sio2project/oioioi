from django.conf import settings
from django.shortcuts import get_object_or_404

from oioioi.contests.models import Contest
from oioioi.contests.utils import visible_contests

NUM_RECENT_CONTESTS = 5

def activate_contest(request, contest):
    request.contest = contest
    if contest and request.session.get('contest_id') != contest.id:
        contest_id = contest.id
        request.session['contest_id'] = contest_id
        recent_contests = request.session.get('recent_contests', [])
        try:
            del recent_contests[recent_contests.index(contest_id)]
        except ValueError:
            pass
        recent_contests = [contest_id] + recent_contests
        recent_contests = recent_contests[:NUM_RECENT_CONTESTS]
        request.session['recent_contests'] = recent_contests

class CurrentContestMiddleware(object):
    """Middleware which saves the most recently visited contest in cookies.

       The :class:`~oioioi.contests.models.Contest` instance is available in
       ``request.contest``.

       It is assumed that all contest-specific URLs accept a ``contest_id``
       argument from urlconf. If a request matches such an URL, the contest
       ID is saved in ``request.session`` to remember the most recently visited
       contest. If the contest ID in the URL is invalid, a 404 Not Found is
       generated.

       Determination of the current contest is performed with the following
       algorithm:

       #. If last contest is saved in session, this value is used.
       #. If the session value is not available or invalid,
          ``settings.DEFAULT_CONTEST`` is used.
       #. If not set, the most recently created contest will be chosen.
       #. If there are no contests, ``request.contest`` will be ``None``.
    """

    def _get_contest(self, contest_id):
        try:
            return Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        contest = None

        if not contest and 'contest_id' in view_kwargs:
            contest = get_object_or_404(Contest, id=view_kwargs['contest_id'])

        if not contest and 'contest_id' in request.session:
            contest = self._get_contest(request.session['contest_id'])

        if not contest and getattr(settings, 'DEFAULT_CONTEST', None):
            contest = self._get_contest(getattr(settings, 'DEFAULT_CONTEST'))

        if not contest:
            contests = visible_contests(request)
            if contests:
                contest = contests[0]

        activate_contest(request, contest)
