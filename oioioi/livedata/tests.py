from django.contrib.auth.models import User
from django.test import override_settings
from django.core.cache import cache

from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import reverse
from oioioi.contests.models import Contest, Round
from oioioi.livedata.utils import get_display_name

# TODO


class TestLivedata(TestCase):
    fixtures = ['test_users', 'test_users_nonames', 'test_contest']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.pa.controllers.PAFinalsContestController'
        contest.save()

    def test_get_user_name(self):
        cases = [
            ('test_user', "T. User"),
            ('UserNoFirstLast', None),
            ('UserNoFirst', None),
            ('UserNoLast', None),
        ]
        for username, display in cases:
            user = User.objects.get(username=username)
            self.assertEqual(get_display_name(user), display or username)

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    })
    def test_cache_unless_admin_or_observer(self):
        contest = Contest.objects.get()
        round = Round.objects.filter(contest_id=contest.id).get()
        view_name = 'livedata_teams_view'
        cache_key = '%s/%s/%s' % (view_name, contest.id, round.id)
        url = reverse(view_name, kwargs={
                      'contest_id': contest.id, 'round_id': round.id})
        # For users that aren't admins or observers, the second request will
        # come from the cache, this verifies if the cached result's content is
        # the same as the uncached result
        self.assertIsNone(cache.get(cache_key))
        request_first = self.client.get(url)
        self.assertIsNotNone(cache.get(cache_key))
        request_cached = self.client.get(url)
        self.assertEqual(
            request_first.content,
            request_cached.content,
            "Cached response differs"
        )
        # Test if admin gets content from cache, by forcefully setting a set
        # "magic string" on the cache key used by the view
        magic_string = 'random'
        cached_data = cache.get(cache_key)
        cached_data['content'] = magic_string
        cache.set(cache_key, cached_data)
        request_cached = self.client.get(url)
        self.assertEqual(
            request_cached.content.decode(request_cached.charset),
            magic_string,
            "Response from cache does not contain expected cached data"
        )
        self.assertTrue(self.client.login(username='test_admin'))
        request_admin = self.client.get(url)
        self.assertNotEqual(
            request_admin.content.decode(request_admin.charset),
            magic_string,
            "Admin should not be receiving a response from cache"
        )
