import re
from datetime import timedelta  # pylint: disable=E0611

from django.conf import settings
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from oioioi.base.tests import TestCase, fake_time
from oioioi.base.tests.tests import TestPublicMessage
from oioioi.contests.models import Contest
from oioioi.forum.forms import PostForm
from oioioi.forum.models import (
    Ban,
    Category,
    Post,
    PostReaction,
    Thread,
    ForumMessage,
    NewPostMessage,
    Forum,
)
from oioioi.participants.models import Participant
from oioioi.programs.controllers import ProgrammingContestController


def get_contest_with_forum():
    contest = Contest.objects.get()
    contest.controller_name = 'oioioi.contests.controllers.ContestController'
    contest.save()
    return contest


def get_contest_with_no_forum():
    contest = Contest.objects.get()
    contest.controller_name = 'oioioi.oi.controllers.OIOnsiteContestController'
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
        Participant.objects.create(
            contest=contest, user=User.objects.get(username='test_user')
        )

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Forum')

    def test_forum_menu(self):
        contest = get_contest_with_forum()

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Forum')

    def test_lock_forum_with_no_unlock_date(self):
        contest = get_contest_with_forum()
        forum = contest.forum
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        with fake_time(self.now):
            # locked, no unlock date set
            forum.lock_date = self.past
            forum.visible = False
            forum.save()

            # locked & not visible, so user does not see forum
            response = self.client.get(url, follow=True)
            self.assertNotContains(response, 'Forum')
            url = reverse('forum', kwargs={'contest_id': contest.id})
            response = self.client.get(url, follow=True)
            self.assertEqual(403, response.status_code)
            self.assertEqual(True, forum.is_locked(self.now))

            forum.visible = True
            forum.save()
            # locked & visible, so user sees forum
            response = self.client.get(url, follow=True)
            self.assertContains(response, 'Forum')
            self.assertEqual(True, forum.is_locked(self.now))

    def test_lock_forum_with_unlock_date(self):
        contest = get_contest_with_forum()
        forum = contest.forum
        forum.lock_date = self.past
        forum.visible = False
        forum.unlock_date = self.future
        forum.save()
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        with fake_time(self.now):
            response = self.client.get(url, follow=True)
            self.assertNotContains(response, 'Forum')
            self.assertEqual(True, forum.is_locked(self.now))

    def test_unlock_forum(self):
        # not visible but not locked either, so it should be visible..
        contest = get_contest_with_forum()
        forum = contest.forum
        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(self.now):
            forum.visible = False
            forum.lock_date = self.past
            forum.save()
            self.assertEqual(True, forum.is_locked(self.now))
            response = self.client.get(url, follow=True)
            self.assertNotContains(response, 'Forum')

            forum.unlock_date = self.past
            forum.save()
            self.assertEqual(False, forum.is_locked(self.now))
            response = self.client.get(url, follow=True)
            self.assertContains(response, 'Forum')


class TestCategory(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        delta = timedelta(days=3)
        self.now = timezone.now()
        self.future = self.now + delta
        self.past = self.now - delta
        self.contest = get_contest_with_forum()
        self.category = Category(forum=self.contest.forum, name='test_category')
        self.category.save()

    def test_add_new(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('oioioiadmin:forum_category_add')
        response = self.client.get(url, follow=True)
        self.assertEqual(403, response.status_code)

        self.client.logout()
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

    def test_no_thread(self):
        forum = self.contest.forum
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse(
            'forum_category',
            kwargs={'contest_id': self.contest.id, 'category_id': self.category.id},
        )
        with fake_time(self.now):
            response = self.client.get(url, follow=True)
            # not locked, adding new thread possible
            self.assertContains(response, 'Add new thread')

            forum.lock_date = self.past
            forum.save()
            self.assertEqual(True, forum.is_locked(self.now))
            url = reverse(
                'forum_category',
                kwargs={'contest_id': self.contest.id, 'category_id': self.category.id},
            )
            response = self.client.get(url, follow=True)
            # locked, adding new thread not possible
            self.assertEqual(200, response.status_code)
            self.assertNotContains(response, 'Add new thread')

    def test_new_categories_are_in_order(self):
        forum = self.contest.forum

        categories = [Category(forum=forum, name=str(i)) for i in range(5)]
        for c in categories:
            c.save()
        categories_ids = [c.id for c in categories]

        self.assertEqual(
            list(
                Category.objects.filter(forum=forum)
                .filter(id__in=categories_ids)
                .order_by("order")
                .values_list("id", flat=True)
            ),
            categories_ids,
        )

    def test_category_move_up_down(self):
        forum = self.contest.forum
        Category.objects.all().delete()
        [a, b, c] = [
            Category.objects.create(forum=forum, name=str(i)) for i in range(3)
        ]
        self.assertTrue(self.client.login(username="test_admin"))
        self.assertTrue(a.order < b.order < c.order)

        def reverse_move(category, direction):
            return reverse(
                "forum_category_move_" + direction,
                kwargs={
                    "contest_id": self.contest.id,
                    "category_id": category.id,
                },
            )

        def refresh_orders():
            for cat in [a, b, c]:
                cat.refresh_from_db()

        # nothing changes -- already top/bottom
        response = self.client.post(reverse_move(a, "up"), follow=True)
        self.assertEqual(response.status_code, 400)
        refresh_orders()
        self.assertTrue(a.order < b.order < c.order)
        response = self.client.post(reverse_move(c, "down"), follow=True)
        self.assertEqual(response.status_code, 400)
        refresh_orders()
        self.assertTrue(a.order < b.order < c.order)

        # is on top
        response = self.client.post(reverse_move(c, "up"), follow=True)
        response = self.client.post(reverse_move(c, "up"), follow=True)
        self.assertEqual(response.status_code, 200)
        refresh_orders()
        self.assertTrue(c.order < a.order < b.order)

        # is in the middle
        response = self.client.post(reverse_move(a, "down"), follow=True)
        self.assertEqual(response.status_code, 200)
        refresh_orders()
        self.assertTrue(c.order < b.order < a.order)

    def test_toggling_reactions(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        toggle_reactions_url = reverse(
            "forum_category_toggle_reactions", kwargs={"category_id": self.category.id}
        )
        forum_view_url = reverse('forum')

        response = self.client.post(toggle_reactions_url, follow=True)
        self.assertEqual(403, response.status_code)
        self.client.logout()

        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        self.assertFalse(self.category.reactions_enabled)
        response = self.client.get(forum_view_url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Enable post reactions')
        self.assertNotContains(response, 'Disable post reactions')

        response = self.client.post(toggle_reactions_url, follow=True)
        self.assertEqual(200, response.status_code)
        self.category.refresh_from_db()
        self.assertTrue(self.category.reactions_enabled)
        response = self.client.get(forum_view_url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Disable post reactions')

        self.client.post(toggle_reactions_url, follow=True)
        self.category.refresh_from_db()
        self.assertFalse(self.category.reactions_enabled)
        response = self.client.get(forum_view_url, follow=True)
        self.assertContains(response, 'Enable post reactions')


class TestThread(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        delta = timedelta(days=3)
        self.past = timezone.now() - delta
        self.contest = get_contest_with_forum()
        self.forum = self.contest.forum
        self.cat = Category(forum=self.forum, name='test_category')
        self.cat.save()
        self.thr = Thread(category=self.cat, name='test_thread')
        self.thr.save()
        self.user = User.objects.get(username='test_user')

    def try_to_remove_post(self, post):
        url = reverse(
            'forum_post_delete',
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.cat.id,
                'thread_id': self.thr.id,
                'post_id': post.id,
            },
        )
        return self.client.get(url, follow=True)

    def test_remove_posts(self):
        p0 = Post(
            thread=self.thr, content='test0', author=self.user, add_date=self.past
        )
        p0.save()
        p1 = Post(thread=self.thr, content='test1', author=self.user)
        p1.save()
        p2 = Post(thread=self.thr, content='test2', author=self.user)
        p2.save()

        self.assertTrue(self.client.login(username='test_user'))
        # user tries to remove post p1 but cannot (it is not last post)
        response = self.try_to_remove_post(p1)
        self.assertEqual(403, response.status_code)

        # user can remove p2 (last post, added by user)
        response = self.try_to_remove_post(p2)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Delete confirmation')
        p2.delete()

        # user tries to remove post p1 (and he can!)
        response = self.try_to_remove_post(p1)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Delete confirmation')
        p1.delete()

        # user tries to remove post p0 but can't (added earlier than 15min ago)
        response = self.try_to_remove_post(p0)
        self.assertEqual(403, response.status_code)


class TestLatestPosts(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        self.contest = get_contest_with_forum()
        self.forum = self.contest.forum
        self.cat = Category(forum=self.forum, name='test_category')
        self.cat.save()
        self.thread = Thread(category=self.cat, name='test_thread1')
        self.thread.save()
        self.user = User.objects.get(username='test_user')
        self.url = reverse(
            'forum_latest_posts',
            kwargs={
                'contest_id': self.contest.id,
            },
        )

    @override_settings(FORUM_PAGE_SIZE=12)
    def test_paging(self):
        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(self.url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'No posts to show.')

        time_offset_0h = timezone.now()

        p = Post(
            thread=self.thread,
            content='t',
            author=self.user,
            add_date=time_offset_0h,
        )
        p.save()

        response = self.client.get(self.url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Thread {} #{}'.format(p.thread.name, p.id))

        for i in range(43):
            Post(
                thread=self.thread,
                content='t' * i,
                author=self.user,
                add_date=time_offset_0h + timedelta(hours=i),
            ).save()

        response = self.client.get(self.url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            len(re.findall(r'Thread .*? #\d+', response.content.decode('utf-8'))),
            settings.FORUM_PAGE_SIZE,
        )

        last_page = int(Post.objects.count() / settings.FORUM_PAGE_SIZE) + 1
        posts_on_last_page = Post.objects.count() % settings.FORUM_PAGE_SIZE

        response = self.client.get(self.url + '?page={}'.format(last_page), follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            len(re.findall(r'Thread .*? #\d+', response.content.decode('utf-8'))),
            posts_on_last_page,
        )


class TestPost(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        delta = timedelta(days=3)
        self.past = timezone.now() - delta
        self.contest = get_contest_with_forum()
        self.user = User.objects.get(username='test_user')
        self.forum = self.contest.forum
        self.cat = Category(forum=self.forum, name='test_category')
        self.cat.save()
        self.thr = Thread(category=self.cat, name='test_thread')
        self.thr.save()
        self.p = Post(
            thread=self.thr, content='Test post!', author=self.user, add_date=self.past
        )
        self.p.save()
        self.thread_url = reverse(
            'forum_thread',
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.cat.id,
                'thread_id': self.thr.id,
            },
        )

    def reverse_post(self, view_name):
        return reverse(
            view_name,
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.cat.id,
                'thread_id': self.thr.id,
                'post_id': self.p.id,
            },
        )

    def assertContainsReportOption(self, response):
        self.assertNotContains(response, 'This post was reported')
        self.assertContains(response, 'report')

    def assertContainsApproveOption(self, response):
        self.assertNotContains(response, 'This post was approved.')
        self.assertContains(response, 'approve')

    def report_post(self):
        self.p.reported = True
        self.p.reported_by = self.user
        self.p.save()

    def test_report(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = self.reverse_post('forum_post_report')
        name = self.user.first_name
        surname = self.user.last_name
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Report confirmation')
        self.report_post()
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse(
            'forum_thread',
            kwargs={'category_id': self.cat.id, 'thread_id': self.thr.id},
        )
        response = self.client.post(url, follow=True)

        reported_pattern = r"was reported\s*by\s*<a[^>]*>\s*%s %s\s*<\/a>" % (
            name,
            surname,
        )
        self.assertTrue(re.search(reported_pattern, response.content.decode('utf-8')))

    def test_approve_after_report(self):
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get(self.thread_url, follow=True)
        self.assertContainsReportOption(response)
        self.assertContainsApproveOption(response)

        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(self.thread_url, follow=True)
        self.assertContainsReportOption(response)
        self.assertNotContains(response, 'approve')

        self.report_post()
        response = self.client.post(self.thread_url, follow=True)
        self.assertContains(response, 'This post was reported')

        self.assertTrue(self.client.login(username='test_admin'))
        url = self.reverse_post('forum_post_approve')
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'revoke approval')
        self.assertContains(response, 'This post was approved.')

        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(self.thread_url, follow=True)
        self.assertNotContains(response, 'report')
        self.assertNotContains(response, 'revoke approval')

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)
        self.assertFalse(self.p.reported)

    def test_approve_without_report(self):
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get(self.thread_url, follow=True)
        self.assertContainsReportOption(response)
        self.assertContainsApproveOption(response)

        url = self.reverse_post('forum_post_approve')
        self.client.post(url, follow=True)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(self.thread_url, follow=True)
        self.assertNotContains(response, 'report')

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)
        self.assertFalse(self.p.reported)

    def test_report_after_approve(self):
        self.p.approved = True
        self.p.save()

        self.assertTrue(self.client.login(username='test_admin'))
        url = self.reverse_post('forum_post_report')
        self.client.post(url)

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)
        self.assertFalse(self.p.reported)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(self.thread_url, follow=True)
        self.assertNotContains(response, 'report')

    def test_revoking_approval_after_edit(self):
        self.p.approved = True
        self.p.save()

        self.assertTrue(self.client.login(username='test_user'))
        url = self.reverse_post('forum_post_edit')
        self.client.get(url, follow=True)

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)

        self.client.post(url, {'content': 'Test content'})

        self.p.refresh_from_db()
        self.assertFalse(self.p.approved)

    def test_admin_approval_edit(self):
        self.p.reported = True
        self.p.save()

        data = {
            'content': self.p.content,
            'thread': self.thr.id,
            'reported': self.p.reported,
            'approved': True,
        }

        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:forum_post_change', args=(self.p.id,))
        self.client.post(url, data)

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)
        self.assertFalse(self.p.reported)

        data['reported'] = True
        self.client.post(url, data)

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)
        self.assertFalse(self.p.reported)

    def test_admin_approve_action(self):
        self.p.reported = True
        self.p.save()

        data = {'_selected_action': (self.p.id,), 'action': 'approve_action'}

        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:forum_post_changelist')
        self.client.post(url, data, follow=True)

        self.p.refresh_from_db()
        self.assertTrue(self.p.approved)
        self.assertFalse(self.p.reported)

    def test_admin_revoke_approval_action(self):
        self.p.approved = True
        self.p.save()

        data = {'_selected_action': (self.p.id,), 'action': 'revoke_approval_action'}

        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:forum_post_changelist')
        self.client.post(url, data, follow=True)

        self.p.refresh_from_db()
        self.assertFalse(self.p.approved)
        self.assertFalse(self.p.reported)

    def test_revoke_approval(self):
        self.p.approved = True
        self.p.save()

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(self.thread_url, follow=True)
        self.assertNotContains(response, 'revoke approval')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(self.thread_url, follow=True)
        self.assertContains(response, 'revoke approval')

        url = self.reverse_post('forum_post_revoke_approval')
        response = self.client.post(url, follow=True)
        self.assertNotContains(response, 'revoke approval')

        self.p.refresh_from_db()
        self.assertFalse(self.p.approved)
        self.assertFalse(self.p.reported)

    def test_reactions_visible_only_if_enabled(self):
        self.cat.reactions_enabled = False
        self.cat.save()
        response = self.client.get(self.thread_url, follow=True)
        self.assertNotContains(response, 'post_reactions')

        self.cat.reactions_enabled = True
        self.cat.save()
        response = self.client.get(self.thread_url, follow=True)
        self.assertContains(response, 'post_reactions')

    def test_reactions_not_clickable_for_anon(self):
        react_url = self.reverse_post('forum_post_toggle_reaction')
        downvote_url = react_url + '?reaction=downvote'

        self.cat.reactions_enabled = True
        self.cat.save()

        response = self.client.get(self.thread_url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, downvote_url)
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(self.thread_url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, downvote_url)

    def test_reactions_from_multiple_users(self):
        react_url = self.reverse_post('forum_post_toggle_reaction')
        downvote_url = react_url + '?reaction=downvote'

        self.cat.reactions_enabled = True
        self.cat.save()

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.post(downvote_url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.post(downvote_url, follow=True)
        self.assertEqual(200, response.status_code)

        self.assertEqual(
            2, self.p.reactions.filter(type_of_reaction='DOWNVOTE').count()
        )
        self.assertEqual(2, self.p.reactions.count())

    def test_remove_reaction(self):
        react_url = self.reverse_post('forum_post_toggle_reaction')
        downvote_url = react_url + '?reaction=downvote'
        self.cat.reactions_enabled = True
        self.cat.save()
        self.assertTrue(self.client.login(username='test_user'))

        def count_reactions(r):
            return self.p.reactions.filter(type_of_reaction=r).count()

        self.assertEqual(0, count_reactions('DOWNVOTE'))
        self.assertEqual(0, self.p.reactions.count())

        self.client.post(downvote_url, follow=True)
        self.assertEqual(1, count_reactions('DOWNVOTE'))
        self.assertEqual(1, self.p.reactions.count())

        self.client.post(downvote_url, follow=True)
        self.assertEqual(0, count_reactions('DOWNVOTE'))
        self.assertEqual(0, self.p.reactions.count())

    def test_switch_reaction(self):
        react_url = self.reverse_post('forum_post_toggle_reaction')
        downvote_url = react_url + '?reaction=downvote'
        upvote_url = react_url + '?reaction=upvote'
        self.cat.reactions_enabled = True
        self.cat.save()
        self.assertTrue(self.client.login(username='test_user'))

        def count_reactions(r):
            return self.p.reactions.filter(type_of_reaction=r).count()

        self.assertEqual(0, self.p.reactions.count())

        self.client.post(upvote_url, follow=True)
        self.assertEqual(1, count_reactions('UPVOTE'))
        self.assertEqual(0, count_reactions('DOWNVOTE'))
        self.assertEqual(1, self.p.reactions.count())

        self.client.post(downvote_url, follow=True)
        self.assertEqual(0, count_reactions('UPVOTE'))
        self.assertEqual(1, count_reactions('DOWNVOTE'))
        self.assertEqual(1, self.p.reactions.count())


class TestBan(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        self.user = User.objects.get(username='test_user')
        self.user2 = User.objects.get(username='test_user2')
        self.contest = get_contest_with_forum()
        self.forum = self.contest.forum
        self.cat = Category(forum=self.forum, name='test_category')
        self.cat.save()
        self.ban = Ban(reason="Saying Ni in forum")
        self.ban.user = self.user
        self.ban.admin = User.objects.get(username='test_admin')
        self.ban.forum = self.forum
        self.ban.save()

    def test_report_post(self):
        thr = Thread(category=self.cat, name='test_thread')
        thr.save()
        p = Post(
            thread=thr,
            content='This post will be reported.',
            author=self.user,
            add_date=timezone.now(),
        )
        p.save()
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse(
            'forum_post_report',
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.cat.id,
                'thread_id': thr.id,
                'post_id': p.id,
            },
        )
        response = self.client.post(url, follow=True)
        self.assertEqual(403, response.status_code)
        self.ban.delete()
        response = self.client.post(url, follow=True)
        self.assertEqual(200, response.status_code)

    def test_add_thread(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.assertEqual(0, Thread.objects.all().count())
        new_thread_url = reverse(
            'forum_add_thread',
            kwargs={'contest_id': self.contest.id, 'category_id': self.cat.id},
        )
        self.client.post(
            new_thread_url,
            {'name': "Test Thread", 'content': "lorem ipsum lorem ipsum!"},
        )
        self.assertEqual(0, Thread.objects.all().count())
        self.ban.delete()
        self.client.post(
            new_thread_url,
            {'name': "Test Thread", 'content': "lorem ipsum lorem ipsum!"},
        )
        thread = Thread.objects.all()[0]
        self.assertEqual("Test Thread", thread.name)
        self.assertEqual(1, thread.count_posts())
        self.assertEqual("lorem ipsum lorem ipsum!", thread.last_post.content)
        self.assertEqual(
            User.objects.get(username='test_user'), thread.last_post.author
        )

    def test_edit_post(self):
        thr = Thread(category=self.cat, name='test_thread')
        thr.save()
        p = Post(
            thread=thr,
            content='This post will be reported.',
            author=self.user,
            add_date=timezone.now(),
        )
        p.save()
        self.assertTrue(self.client.login(username='test_user'))
        edit_url = reverse(
            'forum_post_edit',
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.cat.id,
                'thread_id': thr.id,
                'post_id': p.id,
            },
        )
        self.assertEqual(403, self.client.get(edit_url).status_code)
        self.ban.delete()
        self.assertEqual(200, self.client.get(edit_url).status_code)

    def test_add_post(self):
        thr = Thread(category=self.cat, name='test_thread')
        thr.save()
        thread_url = reverse(
            'forum_thread',
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.cat.id,
                'thread_id': thr.id,
            },
        )
        self.assertTrue(self.client.login(username='test_user'))
        self.assertFalse(Post.objects.filter(author=self.user).exists())
        response = self.client.get(thread_url)
        self.assertNotIsInstance(response.context['form'], PostForm)

        self.client.post(thread_url, {'content': "lorem ipsum?"})
        self.assertFalse(Post.objects.filter(author=self.user).exists())

        self.ban.delete()

        response = self.client.get(thread_url)
        self.assertIsInstance(response.context['form'], PostForm)

        self.client.post(thread_url, {'content': "lorem ipsum?"})
        self.assertTrue(Post.objects.filter(author=self.user).exists())
        post = Post.objects.filter(author=self.user)[0]
        self.assertEqual("lorem ipsum?", post.content)
        self.assertEqual(self.user, post.author)

    def test_ban_view_without_removing_reports(self):
        self.ban.delete()
        thr = Thread(category=self.cat, name='test_thread')
        thr.save()
        p0 = Post(
            thread=thr,
            content='test0',
            author=self.user2,
            reported=True,
            reported_by=self.user,
        )
        p0.save()
        p1 = Post(
            thread=thr,
            content='test1',
            author=self.user2,
            reported=True,
            reported_by=self.user,
        )
        p1.save()
        p2 = Post(thread=thr, content='test2', author=self.user2)
        p2.save()
        p3 = Post(
            thread=thr,
            content='test2',
            author=self.user,
            reported=True,
            reported_by=self.user2,
        )
        p3.save()

        def check_reports():
            p0.refresh_from_db()
            p1.refresh_from_db()
            p2.refresh_from_db()
            p3.refresh_from_db()
            return [p0.reported, p1.reported, p2.reported, p3.reported]

        self.assertEqual([True, True, False, True], check_reports())

        self.assertTrue(self.client.login(username='test_admin'))
        self.assertFalse(Ban.objects.exists())

        ban_url = reverse(
            'forum_user_ban',
            kwargs={'contest_id': self.contest.id, 'user_id': self.user.id},
        )

        self.client.post(ban_url, {'reason': 'Abuse'})
        self.assertEqual(1, Ban.objects.count())
        ban = Ban.objects.all()[0]
        self.assertEqual(self.user, ban.user)
        self.assertEqual('test_admin', ban.admin.username)
        self.assertEqual('Abuse', ban.reason)
        self.assertEqual(self.contest.forum, ban.forum)
        self.assertEqual([True, True, False, True], check_reports())
        ban.delete()

        self.client.post(ban_url, {'reason': 'Abuse', 'delete_reports': True})
        self.assertEqual(1, Ban.objects.count())
        ban = Ban.objects.all()[0]
        self.assertEqual(self.user, ban.user)
        self.assertEqual('test_admin', ban.admin.username)
        self.assertEqual('Abuse', ban.reason)
        self.assertEqual(self.contest.forum, ban.forum)
        self.assertEqual([False, False, False, True], check_reports())


class PublicMessagesContestController(ProgrammingContestController):
    forum_message = 'Test public message'
    forum_new_post_message = 'Test public message'


class TestForumMessage(TestPublicMessage):
    model = ForumMessage
    button_viewname = 'forum'
    edit_viewname = 'edit_forum_message'
    viewname = 'forum'
    controller_name = 'oioioi.forum.tests.PublicMessagesContestController'

    def setUp(self):
        super().setUp()
        contest = Contest.objects.get()
        Forum.objects.get_or_create(contest=contest)


class TestNewPostMessage(TestPublicMessage):
    model = NewPostMessage
    button_viewname = 'forum'
    edit_viewname = 'edit_forum_new_post_message'
    viewname = 'forum_thread'
    controller_name = 'oioioi.forum.tests.PublicMessagesContestController'

    def setUp(self):
        super().setUp()
        contest = Contest.objects.get()
        forum = Forum.objects.get_or_create(contest=contest)[0]
        cat = Category.objects.get_or_create(forum=forum, name='test_category')[0]
        thr = Thread.objects.get_or_create(category=cat, name='test_thread')[0]
        self.viewname_kwargs = {
            'contest_id': contest.id,
            'category_id': cat.id,
            'thread_id': thr.id,
        }


class TestContestArchived(TestCase):
    fixtures = ['test_users', 'test_archived_contest']

    def setUp(self):
        self.contest = get_contest_with_forum()
        self.user = User.objects.get(username='test_user')
        self.category = Category(forum=self.contest.forum, name='test_category')
        self.category.save()

    def test_add_new_forum_category(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('oioioiadmin:forum_category_add', kwargs={'contest_id': 'c'})
        # non-admins should not be able to add categories when contest is archived
        response = self.client.get(url, follow=True)
        self.assertEqual(403, response.status_code)

        self.client.logout()
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        # admins also should not be able to add categories when contest is archived
        response = self.client.get(url, follow=True)
        self.assertEqual(403, response.status_code)

    def test_add_post(self):
        thr = Thread(category=self.category, name='test_thread')
        thr.save()
        thread_url = reverse(
            'forum_thread',
            kwargs={
                'contest_id': self.contest.id,
                'category_id': self.category.id,
                'thread_id': thr.id,
            },
        )
        # non-admins should not be able to post when contest is archived
        self.assertTrue(self.client.login(username='test_user'))
        self.assertFalse(Post.objects.filter(author=self.user).exists())
        response = self.client.get(thread_url)
        self.assertNotIsInstance(response.context['form'], PostForm)

        self.client.post(thread_url, {'content': "lorem ipsum?"})
        self.assertFalse(Post.objects.filter(author=self.user).exists())
        self.client.logout()

        # admins also should not be able to post when contest is archived
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(thread_url)
        self.assertNotIsInstance(response.context['form'], PostForm)

        self.client.post(thread_url, {'content': "lorem ipsum?"})
        self.assertFalse(Post.objects.filter(author=self.user).exists())
