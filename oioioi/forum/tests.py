import re

from django.utils import timezone
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest
from oioioi.forum.models import Category, Thread, Post

from datetime import timedelta


def get_contest_with_forum():
    contest = Contest.objects.get()
    contest.controller_name = \
            'oioioi.contests.controllers.ContestController'
    contest.save()
    return contest


def get_contest_with_no_forum():
    contest = Contest.objects.get()
    contest.controller_name = \
            'oioioi.oi.controllers.OIOnsiteContestController'
    contest.save()
    return contest


class TestForum(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        delta = timedelta(days=3)
        self.now = timezone.now()
        self.future = self.now + delta
        self.past = self.now - delta

    def test_no_forum_menu(self):
        contest = get_contest_with_no_forum()

        self.client.login(username='test_user')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertNotIn('Forum', response.content)

    def test_forum_menu(self):
        contest = get_contest_with_forum()

        self.client.login(username='test_user')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertIn('Forum', response.content)

    def test_lock_forum_with_no_unlock_date(self):
        contest = get_contest_with_forum()
        forum = contest.forum
        self.client.login(username='test_user')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        with fake_time(self.now):
            # locked, no unlock date set
            forum.lock_date = self.past
            forum.visible = False
            forum.save()

            # locked & not visible, so user does not see forum
            response = self.client.get(url, follow=True)
            self.assertNotIn('Forum', response.content)
            url = reverse('forum', kwargs={'contest_id': contest.id})
            response = self.client.get(url, follow=True)
            self.assertEqual(403, response.status_code)
            self.assertEqual(True, forum.is_locked(self.now))

            forum.visible = True
            forum.save()
            # locked & visible, so user sees forum
            response = self.client.get(url, follow=True)
            self.assertIn('Forum', response.content)
            self.assertEqual(True, forum.is_locked(self.now))

    def test_lock_forum_with_unlock_date(self):
        contest = get_contest_with_forum()
        forum = contest.forum
        forum.lock_date = self.past
        forum.visible = False
        forum.unlock_date = self.future
        forum.save()
        self.client.login(username='test_user')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        with fake_time(self.now):
            response = self.client.get(url, follow=True)
            self.assertNotIn('Forum', response.content)
            self.assertEqual(True, forum.is_locked(self.now))

    def test_unlock_forum(self):
        # not visible but not locked either, so it should be visible..
        contest = get_contest_with_forum()
        forum = contest.forum
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        with fake_time(self.now):
            forum.visible = False
            forum.lock_date = self.past
            forum.save()
            self.assertEqual(True, forum.is_locked(self.now))
            response = self.client.get(url, follow=True)
            self.assertNotIn('Forum', response.content)

            forum.unlock_date = self.past
            forum.save()
            self.assertEqual(False, forum.is_locked(self.now))
            response = self.client.get(url, follow=True)
            self.assertIn('Forum', response.content)


class TestCategory(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        delta = timedelta(days=3)
        self.now = timezone.now()
        self.future = self.now + delta
        self.past = self.now - delta

    def test_add_new(self):
        self.client.login(username='test_user')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('oioioiadmin:forum_category_add', kwargs={})
        response = self.client.get(url, follow=True)
        self.assertEqual(403, response.status_code)

    def test_no_thread(self):
        contest = get_contest_with_forum()
        forum = contest.forum
        category = Category(forum=forum, name='test_category')
        category.save()
        self.client.login(username='test_user')
        url = reverse('forum_category', kwargs={'contest_id': contest.id,
                                                'category_id': category.id})
        with fake_time(self.now):
            response = self.client.get(url, follow=True)
            # not locked, adding new thread possible
            self.assertIn('Add new thread', response.content)

            forum.lock_date = self.past
            forum.save()
            self.assertEqual(True, forum.is_locked(self.now))
            url = reverse('forum_category',
                          kwargs={'contest_id': contest.id,
                                  'category_id': category.id})
            response = self.client.get(url, follow=True)
            # locked, adding new thread not possible
            self.assertEqual(200, response.status_code)
            self.assertNotIn('Add new thread', response.content)


class TestThread(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        delta = timedelta(days=3)
        self.past = timezone.now() - delta
        self.cont = get_contest_with_forum()
        self.forum = self.cont.forum
        self.cat = Category(forum=self.forum, name='test_category')
        self.cat.save()
        self.thr = Thread(category=self.cat, name='test_thread')
        self.thr.save()
        self.user = User.objects.get(username='test_user')

    def try_to_remove_post(self, post):
        url = reverse('forum_post_delete', kwargs={'contest_id': self.cont.id,
                                                   'category_id': self.cat.id,
                                                   'thread_id': self.thr.id,
                                                   'post_id': post.id})
        return self.client.get(url, follow=True)

    def test_remove_posts(self):
        p0 = Post(thread=self.thr, content='test0', author=self.user,
                  add_date=self.past)
        p0.save()
        p1 = Post(thread=self.thr, content='test1', author=self.user)
        p1.save()
        p2 = Post(thread=self.thr, content='test2', author=self.user)
        p2.save()

        self.client.login(username='test_user')
        # user tries to remove post p1 but cannot (it is not last post)
        response = self.try_to_remove_post(p1)
        self.assertEqual(403, response.status_code)

        # user can remove p2 (last post, added by user)
        response = self.try_to_remove_post(p2)
        self.assertEqual(200, response.status_code)
        self.assertIn('Delete confirmation', response.content)
        p2.delete()

        # user tries to remove post p1 (and he can!)
        response = self.try_to_remove_post(p1)
        self.assertEqual(200, response.status_code)
        self.assertIn('Delete confirmation', response.content)
        p1.delete()

        # user tries to remove post p0 but can't (added earlier than 15min ago)
        response = self.try_to_remove_post(p0)
        self.assertEqual(403, response.status_code)

    def test_report_post(self):
        p = Post(thread=self.thr, content='This post will be reported.',
                 author=self.user, add_date=self.past)
        p.save()
        self.client.login(username='test_user')
        url = reverse('forum_post_report', kwargs={'contest_id': self.cont.id,
                                                   'category_id': self.cat.id,
                                                   'thread_id': self.thr.id,
                                                   'post_id': p.id})
        name = self.user.first_name
        surname = self.user.last_name
        response = self.client.post(url, follow=True)
        self.assertIn('This post was reported', response.content)
        self.client.login(username='test_admin')
        url = reverse('forum_thread', kwargs={'category_id': self.cat.id,
                                              'thread_id': self.thr.id})
        response = self.client.post(url, follow=True)

        reported_pattern = r"was reported\s*by\s*<a[^>]*>\s*%s %s\s*<\/a>" \
                           % (name, surname)
        self.assertTrue(re.search(reported_pattern, response.content))
