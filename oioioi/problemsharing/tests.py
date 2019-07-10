from django.contrib.auth.models import User
from oioioi.base.tests import TestCase
from django.urls import reverse

from oioioi.problemsharing.models import Friendship


class TestFriendshipManagement(TestCase):
    fixtures = ['test_users', 'teachers']
    url = reverse('problemsharing_friends')

    def testAdd(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.assertContains(self.client.get(self.url), "no friends")
        self.assertEqual(len(Friendship.objects.all()), 0)
        self._addToFriends('test_user')
        self.assertEqual(len(Friendship.objects.all()), 0)
        self._addToFriends('test_user2')
        self.assertEqual(len(Friendship.objects.all()), 1)
        self.assertContains(self.client.get(self.url), "test_user2")

    def testRemove(self):
        self.assertTrue(self.client.login(username='test_user'))
        Friendship(creator=User.objects.get(username='test_user'),
                   receiver=User.objects.get(username='test_user2')).save()
        self.assertEqual(len(Friendship.objects.all()), 1)
        self.assertContains(self.client.get(self.url), "test_user2")
        self._removeFromFriends(User.objects.get(username='test_user2').id)
        self.assertEqual(len(Friendship.objects.all()), 0)
        self.assertContains(self.client.get(self.url), "no friends")

    def testOnlyTeachersCanUseFriends(self):
        self.assertTrue(self.client.login(username='test_user3'))  # non teacher
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def testOnlyTeachersCanBeFriends(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.assertContains(
            self.client.post(self.url, {'befriend': '', 'user': 'test_user3'}),
            "no friends"
        )
        self.assertEqual(len(Friendship.objects.all()), 0)

    def _addToFriends(self, name):
        self.assertEqual(
            self.client.post(self.url,
                             {'befriend': '', 'user': name}).status_code,
            200
        )

    def _removeFromFriends(self, id):
        self.assertEqual(
            self.client.post(self.url, {'unfriend': '', 'id': id}).status_code,
            200
        )
