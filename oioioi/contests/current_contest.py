import re
import threading
import copy
from enum import Enum

from django.core import urlresolvers
from django.core.urlresolvers import NoReverseMatch
from django.utils.functional import lazy


ContestMode = Enum('ContestMode', 'neutral contest_if_possible contest_only')


cc_id = threading.local()


def get_cc_id():
    return getattr(cc_id, 'value', None)


def set_cc_id(val):
    cc_id.value = val


contest_re = re.compile(r'^/c/([a-z0-9_-]+)/')


def reverse(target, *args, **kwargs):
    """A modified URL reverser that takes into account the current contest
       and generates URLs that are appropriately prefixed. With it we
       substitute the original ``urlresolvers.reverse`` function.

       If a ``contest_id`` kwarg is given or there is a current contest when
       reverse is called, it tries to generate a contest-prefixed URL pointing
       to the target (the kwarg takes precedence). If it fails or there is no
       contest, it tries to return a non contest-prefixed URL. Only when
       both cases fail ``NoReverseMatch`` is thrown.

       Our reverser uses the special structure of each app's urls.py file:

        * Urls pointing to views that require a contest are defined in
          the ``contest_patterns`` pattern list. Those only have
          a contest-prefixed version.
        * Urls pointing to views that require no contest being active
          are defined in the ``noncontest_patterns`` pattern list. Those
          only have a non contest-prefixed version.
        * Urls pointing to views that can run both with and without
          current contest are defined in the ``urlpatterns`` pattern list.
          Those have both versions.

       These files are preprocessed to be used by the reverser.
       Urls defined in ``oioioi.urls`` are not preprocessed, so they only have
       a non-prefixed version, even though they could exist within a contest.

       Note that there is no point defining patterns that receive
       a ``contest_id`` kwarg. That particular kwarg is interpreted differently
       and will never be actually matched in the url pattern when reversing.

       You need to take for account the behavior of reverse when defining
       your own custom urlconf (that means patterns lying outside an app's
       urls.py file, e.g. for testing purposes), because it won't be
       preprocessed. For that we created the
       :func:`~oioioi.contests.urls.make_patterns` function.
    """
    m = getattr(target, '__module__', None)
    n = getattr(target, '__name__', None)
    if m is not None and n is not None:
        name = "%s.%s" % (m, n)
    else:
        name = target

    contest_id = None
    if 'kwargs' in kwargs and kwargs['kwargs'] \
            and 'contest_id' in kwargs['kwargs']:
        kwargs = copy.deepcopy(kwargs)
        contest_id = kwargs['kwargs'].pop('contest_id')
    if not contest_id:
        contest_id = get_cc_id()

    if contest_id:
        try:
            ret = django_reverse('contest:' + name, *args, **kwargs)
            return re.sub(contest_re, r'/c/{}/'.format(contest_id), ret)
        except NoReverseMatch:
            # We will try the noncontest version.
            pass

    try:
        return django_reverse('noncontest:' + name, *args, **kwargs)
    except NoReverseMatch:
        # It can still be one of those urls defined in the global urls.py
        # because we didn't namespace them.
        pass

    return django_reverse(name, *args, **kwargs)


django_reverse = None


def patch():
    global django_reverse
    # Will not patch twice.
    if urlresolvers.reverse is not reverse:
        django_reverse = urlresolvers.reverse
        urlresolvers.reverse = reverse
        urlresolvers.reverse_lazy = lazy(reverse, str)


patch()
