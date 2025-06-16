from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch, resolve, reverse

from oioioi.contests.current_contest import ContestMode, contest_re, set_cc_id
from oioioi.contests.models import Contest, ContestView
from oioioi.contests.utils import visible_contests


def activate_contest(request, contest):
    request.contest = contest
    set_cc_id(contest.id if contest else None)

    if not contest:
        return

    recent_contests = request.session.get('recent_contests', [])
    if not recent_contests or recent_contests[0] != contest.id:
        try:
            del recent_contests[recent_contests.index(contest.id)]
        except ValueError:
            pass
        recent_contests = [contest.id] + recent_contests
        recent_contests = recent_contests[: getattr(settings, 'NUM_RECENT_CONTESTS', 5)]
        request.session['recent_contests'] = recent_contests

    if not request.real_user.is_anonymous and not request.session.get(
        'first_view_after_logging', False
    ):
        cv, created = ContestView.objects.get_or_create(
            user=request.real_user, contest=contest
        )
        # Do not repeatedly update timestamp for latest contest.
        if cv != ContestView.objects.filter(user=request.real_user).latest() or created:
            cv.timestamp = request.timestamp
            cv.save()


class CurrentContestMiddleware(object):
    """Middleware which tracks the currently visited contest and stores it
    to be used in other parts of the current contest mechanism.

    It is assumed that all contest-specific url patterns are defined in the
    ``contest_patterns`` variable in each module's urlconf. These patterns
    are extended with non contest-specific patterns defined in
    the ``urlpatterns`` variable and then used to generate URLs prefixed
    with a contest ID (thus the non contest-specific URLs come in two
    versions, with and without a contest ID prefix).
    If a request matches a contest ID-prefixed URL and the ID is valid,
    the contest becomes the current contest. If the ID is not valid,
    a 404 Not Found is generated.

    After a contest becomes the current contest, the corresponding
    :class:`~oioioi.contests.models.Contest` instance is available in
    ``request.contest``. In addition to that, our custom
    :func:`~oioioi.contests.current_contest.reverse` function automatically
    prefixes generated URLs with the contest's ID if appropriate.

    Using ``settings.CONTEST_MODE``, the administrator may decide
    that users should, if possible, be forcibly put into a contest.
    Then, if there is no contest ID in a request's URL, but the URL
    also comes with a contest-specific version and a contest exists,
    a redirection is performed to one of the existing contests. Which one
    it is is determined by the following algorithm:

     #. If last contest is saved in session, this value is used.
     #. If the session value is not available or invalid,
        ``settings.DEFAULT_CONTEST`` is used.
     #. If not set, the most recently created contest will be chosen.

    URL patterns may be explicitly defined as requiring that no contest
    is given using the ``noncontest_patterns`` variable in each module's
    urlconf. Again, using ``settings.CONTEST_MODE``, the administrator
    may decide that if a contest is available, users cannot access those
    URLs. Trying to access them then generates a 403 Permission Denied
    unless one is a superuser.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._process_request(request)

        if response is None:
            return self.get_response(request)

        return response

    def _get_contest(self, contest_id):
        try:
            return Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            return None

    def _process_request(self, request):
        contest = None
        m = contest_re.match(request.path)

        if m is not None:
            contest_id = m.group('c_name')
            contest = get_object_or_404(Contest, id=contest_id)

        activate_contest(request, contest)

        if contest or settings.CONTEST_MODE == ContestMode.neutral:
            return

        # There was no contest, but CONTEST_MODE tells us we need
        # to try to put the user into a contest.
        recent_contests = request.session.get('recent_contests', [])
        if recent_contests:
            contest = self._get_contest(recent_contests[0])

        if not contest and getattr(settings, 'DEFAULT_CONTEST', None):
            contest = self._get_contest(getattr(settings, 'DEFAULT_CONTEST'))

        if not contest:
            # do not redeem sir
            visible = visible_contests(request)
            if visible:
                # Get most recent visible contest
                contest = max(visible, key=lambda c: c.creation_date)

        if not contest:
            return

        # We found a contest. We will try to regenerate our URL,
        # this time using our contest's id.
        try:
            res = resolve(request.path)
        except Http404:
            # We still allow the request to continue, because
            # it could be a static URL.
            return
        if not res.url_name:
            return
        nonglobal = False
        if res.namespaces and res.namespaces[0] == 'noncontest':
            # It certainly isn't a global url because it has
            # a noncontest version. It could still be a neutral URL.
            nonglobal = True
            res.namespaces = res.namespaces[1:]
        assert 'contest_id' not in res.kwargs
        res.kwargs['contest_id'] = contest.id
        # If there is a contest-prefixed version of this url,
        # reverse will return it.
        assert not res.namespaces or res.namespaces[0] != 'contest'
        name = res.url_name
        if res.namespaces:
            name = ':'.join(res.namespaces + [name])
        try:
            new_path = reverse(name, args=res.args, kwargs=res.kwargs)
            assert contest_re.match(new_path)
            if request.GET:
                new_path += '?' + request.GET.urlencode()
            return HttpResponseRedirect(new_path)
        except NoReverseMatch:
            if nonglobal:
                # That wasn't a global url and it doesn't have
                # a contest version. It must be a noncontest-only url.
                if (
                    settings.CONTEST_MODE == ContestMode.contest_only
                    and not request.user.is_superuser
                ):
                    raise PermissionDenied
