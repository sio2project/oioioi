from django.contrib.auth.models import User
from oioioi.base.tests import TestCase
from oioioi.livedata.utils import get_display_name


# TODO

class TestLivedata(TestCase):
    fixtures = ['test_users', 'test_users_nonames']

    def test_get_user_name(self):
        cases = [('test_user', "T. User"),
                ('UserNoFirstLast', None),
                ('UserNoFirst', None),
                ('UserNoLast', None)]
        for username, display in cases:
            user = User.objects.get(username=username)
            self.assertEqual(get_display_name(user), display or username)
