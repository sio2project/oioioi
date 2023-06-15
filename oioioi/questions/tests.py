from copy import deepcopy
from datetime import datetime, timezone  # pylint: disable=E0611

try:
    import mock
except ImportError:
    from unittest import mock
from django.contrib.auth.models import User
from django.core import mail
from django.test import RequestFactory
from django.urls import reverse
from django.utils.timezone import make_aware

from oioioi.base.notification import NotificationHandler
from oioioi.base.tests import TestCase, check_not_accessible, fake_time
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.questions.forms import FilterMessageForm
from oioioi.questions.management.commands.mailnotifyd import (
    candidate_messages,
    mailnotify,
)
from oioioi.questions.models import Message, ReplyTemplate
from oioioi.questions.utils import unanswered_questions

from .views import visible_messages


class TestContestControllerMixin(object):
    def users_to_receive_public_message_notification(self):
        return self.registration_controller().filter_participants(User.objects.all())


ProgrammingContestController.mix_in(TestContestControllerMixin)


class TestQuestions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
        'test_templates',
        'test_subscriptions',
    ]

    def test_visibility(self):
        contest = Contest.objects.get()
        all_messages = [
            'problem-question',
            'contest-question',
            'public-answer',
            'private-answer',
        ]
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})

        def check_visibility(*should_be_visible):
            response = self.client.get(url)
            for m in all_messages:
                if m in should_be_visible:
                    self.assertContains(response, m)
                else:
                    self.assertNotContains(response, m)

        self.assertTrue(self.client.login(username='test_user'))
        check_visibility('public-answer', 'private-answer')
        self.assertTrue(self.client.login(username='test_user2'))
        check_visibility('public-answer')
        self.assertTrue(self.client.login(username='test_admin'))
        check_visibility('public-answer', 'private-answer')

    def test_pub_date(self):
        contest = Contest.objects.get()
        all_messages = [
            'question-visible-title',
            'question-hidden1-title',
            'question-hidden2-title',
            'response-hidden-title',
            'visible-response-to-hidden',
        ]
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})
        timestamp = datetime(2013, 9, 7, 13, 40, 0, tzinfo=timezone.utc)

        def check_visibility(*should_be_visible):
            with fake_time(timestamp):
                response = self.client.get(url)
            for m in all_messages:
                if m in should_be_visible:
                    self.assertContains(response, m)
                else:
                    self.assertNotContains(response, m)

        self.assertTrue(self.client.login(username='test_user'))
        check_visibility('question-visible-title')
        self.assertTrue(self.client.login(username='test_admin'))
        check_visibility(
            'response-hidden-title',
            'question-hidden1-title',
            'visible-response-to-hidden',
        )

    def test_user_date(self):
        ta = datetime(1970, 1, 1, 12, 30, tzinfo=timezone.utc)
        tb = datetime(1970, 1, 1, 13, 30, tzinfo=timezone.utc)
        self.assertEqual(Message(date=ta, pub_date=None).get_user_date(), ta)
        self.assertEqual(Message(date=ta, pub_date=tb).get_user_date(), tb)

    def test_visible_messages(self):
        contest = Contest.objects.get()
        timestamp = datetime(2013, 9, 7, 13, 40, 0, tzinfo=timezone.utc)

        def make_request(username):
            request = RequestFactory().request()
            request.timestamp = timestamp
            request.contest = contest
            request.user = User.objects.get(username=username)
            return request

        self.assertListEqual(
            [5, 4, 3, 2, 1], [m.id for m in visible_messages(make_request('test_user'))]
        )
        self.assertListEqual(
            [5, 4], [m.id for m in visible_messages(make_request('test_user2'))]
        )
        self.assertListEqual(
            [9, 8, 7, 6, 5, 4, 10, 3, 2, 1],
            [m.id for m in visible_messages(make_request('test_admin'))],
        )

    def test_new_labels(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        list_url = reverse('contest_messages', kwargs={'contest_id': contest.id})
        timestamp = make_aware(datetime.utcfromtimestamp(1347025200))
        with fake_time(timestamp):
            response = self.client.get(list_url)
        self.assertContains(response, '>NEW<', count=2)
        public_answer = Message.objects.get(topic='public-answer')
        with fake_time(timestamp):
            response = self.client.get(
                reverse(
                    'message',
                    kwargs={'contest_id': contest.id, 'message_id': public_answer.id},
                )
            )
        self.assertContains(response, 'public-answer-body')
        self.assertNotContains(response, 'contest-question')
        self.assertNotContains(response, 'problem-question')
        with fake_time(timestamp):
            response = self.client.get(list_url)
        self.assertContains(response, '>NEW<', count=1)

    def test_ask_and_reply(self):
        self.assertTrue(self.client.login(username='test_user2'))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('add_contest_message', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertEqual(len(form.fields['category'].choices) - 1, 2)

        post_data = {
            'category': 'p_%d' % (pi.id,),
            'topic': 'the-new-question',
            'content': 'the-new-body',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic='the-new-question')
        self.assertEqual(new_question.content, 'the-new-body')
        self.assertEqual(new_question.kind, 'QUESTION')
        self.assertIsNone(new_question.top_reference)
        self.assertEqual(new_question.contest, contest)
        self.assertEqual(new_question.problem_instance, pi)
        self.assertEqual(new_question.author.username, 'test_user2')

        self.assertTrue(self.client.login(username='test_admin'))
        list_url = reverse('contest_messages', kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertContains(response, 'the-new-question')

        url = reverse(
            'message', kwargs={'contest_id': contest.id, 'message_id': new_question.id}
        )
        response = self.client.get(url)
        self.assertIn('form', response.context)

        post_data = {
            'kind': 'PUBLIC',
            'topic': 're-new-question',
            'content': 're-new-body',
            'save_template': True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        post_data = {
            'kind': 'PUBLIC',
            'topic': 'another-re-new-question',
            'content': 'another-re-new-body',
            'save_template': False,
        }
        response = self.client.post(url, post_data)
        self.assertRaises(
            ReplyTemplate.DoesNotExist,
            lambda: ReplyTemplate.objects.get(content='another-re-new-body'),
        )
        self.assertEqual(response.status_code, 302)
        new_reply = Message.objects.get(topic='re-new-question')
        self.assertEqual(new_reply.content, 're-new-body')
        self.assertEqual(new_reply.kind, 'PUBLIC')
        self.assertEqual(new_reply.top_reference, new_question)
        self.assertEqual(new_reply.contest, contest)
        self.assertEqual(new_reply.problem_instance, pi)
        self.assertEqual(new_reply.author.username, 'test_admin')

        self.assertTrue(self.client.login(username='test_user'))
        q_url = reverse(
            'message', kwargs={'contest_id': contest.id, 'message_id': new_question.id}
        )
        check_not_accessible(self, q_url)
        repl_url = reverse(
            'message', kwargs={'contest_id': contest.id, 'message_id': new_reply.id}
        )
        response = self.client.get(repl_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 're-new-question')
        self.assertContains(response, 're-new-body')
        self.assertNotContains(response, 'the-new-question')
        self.assertNotContains(response, 'the-new-body')
        response = self.client.get(list_url)
        self.assertContains(response, repl_url)
        self.assertContains(response, 're-new-question')
        self.assertNotContains(response, 'the-new-question')

        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get(q_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'the-new-question')
        self.assertContains(response, 'the-new-body')
        self.assertContains(response, 're-new-body')
        response = self.client.get(list_url)
        self.assertContains(response, q_url)
        self.assertContains(response, 're-new-question')
        self.assertNotContains(response, 'the-new-question')

    def test_reply_notification(self):
        flags = {}
        flags['user_1001_got_notification'] = False
        flags['user_1002_got_notification'] = False

        @classmethod
        def fake_send_notification(
            cls,
            user,
            notification_type,
            notification_message,
            notificaion_message_arguments,
        ):
            if user.pk == 1002:
                flags['user_1002_got_notification'] = True
            if user.pk == 1001:
                flags['user_1001_got_notification'] = True

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        # Test user asks a new question
        self.assertTrue(self.client.login(username='test_user2'))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('add_contest_message', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            'category': 'p_%d' % (pi.id,),
            'topic': 'the-new-question',
            'content': 'the-new-body',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic='the-new-question')

        # Test admin replies his question
        self.assertTrue(self.client.login(username='test_admin'))
        list_url = reverse('contest_messages', kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertContains(response, 'the-new-question')

        url = reverse(
            'message', kwargs={'contest_id': contest.id, 'message_id': new_question.id}
        )
        response = self.client.get(url)
        self.assertIn('form', response.context)

        post_data = {
            'kind': 'PRIVATE',
            'topic': 're-new-question',
            'content': 're-new-body',
            'save_template': True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        # Check if a notification for user was send
        self.assertTrue(flags['user_1002_got_notification'])
        self.assertFalse(flags['user_1001_got_notification'])

        NotificationHandler.send_notification = send_notification_backup

    def test_public_message_notification(self):
        flags = {}
        flags['user_1001_got_notification'] = False
        flags['user_1002_got_notification'] = False

        @classmethod
        def fake_send_notification(
            cls,
            user,
            notification_type,
            notification_message,
            notificaion_message_arguments,
        ):
            if user.pk == 1002:
                flags['user_1002_got_notification'] = True
            if user.pk == 1001:
                flags['user_1001_got_notification'] = True

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        # Test user asks a new question
        self.assertTrue(self.client.login(username='test_user2'))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()

        url = reverse('add_contest_message', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            'category': 'p_%d' % (pi.id,),
            'topic': 'the-new-question',
            'content': 'the-new-body',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic='the-new-question')

        # Test admin replies his question
        self.assertTrue(self.client.login(username='test_admin'))
        list_url = reverse('contest_messages', kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertContains(response, 'the-new-question')

        url = reverse(
            'message', kwargs={'contest_id': contest.id, 'message_id': new_question.id}
        )
        response = self.client.get(url)
        self.assertIn('form', response.context)

        post_data = {
            'kind': 'PUBLIC',
            'topic': 're-new-question',
            'content': 're-new-body',
            'save_template': True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(flags['user_1002_got_notification'])
        self.assertTrue(flags['user_1001_got_notification'])

        NotificationHandler.send_notification = send_notification_backup

    def test_filtering(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})

        get_data = {'author': 'test_admin'}
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'general-question')
        self.assertNotContains(response, 'problem-question')
        self.assertContains(response, 'public-answer')
        self.assertContains(response, 'private-answer')

        get_data['author'] = 'test_user'
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'general-question')
        self.assertContains(response, 'problem-question')
        self.assertNotContains(response, 'public-answer')
        self.assertNotContains(response, 'private-answer')

        get_data['category'] = 'r_1'
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'general-question')
        self.assertNotContains(response, 'problem-question')
        self.assertNotContains(response, 'public-answer')
        self.assertNotContains(response, 'private-answer')

        get_data['category'] = 'p_1'
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'general-question')
        self.assertContains(response, 'problem-question')
        self.assertNotContains(response, 'public-answer')
        self.assertNotContains(response, 'private-answer')

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'general-question')
        self.assertNotContains(response, 'problem-question')
        self.assertNotContains(response, 'public-answer')
        self.assertContains(response, 'private-answer')

    def test_authors_list(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        url = reverse('get_messages_authors', kwargs={'contest_id': contest.id})
        response = self.client.get(url, {'substr': ''})
        self.assertEqual(404, response.status_code)
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

        response = self.client.get(url, {'substr': 'te'})
        self.assertEqual(200, response.status_code)
        response = response.json()
        self.assertListEqual(
            ['test_admin (Test Admin)', 'test_user (Test User)'], response
        )

        response = self.client.get(url, {'substr': 'test admin'})
        response = response.json()
        self.assertListEqual(['test_admin (Test Admin)'], response)

        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url)

    def test_change_category(self):
        pi = ProblemInstance.objects.get()
        r = pi.round
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.client.get('/c/c/')  # 'c' becomes the current contest

        def change_category(msg, cat):
            url = reverse('oioioiadmin:questions_message_change', args=(msg.id,))
            self.assertTrue(self.client.login(username='test_admin'))
            response = self.client.get(url)
            self.assertIn('form', response.context)

            post_data = {
                'kind': msg.kind,
                'category': cat,
                'topic': msg.topic,
                'content': msg.content,
            }
            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 302)

        # Change a1 to round question
        change_category(a1, 'r_%d' % r.id)
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.assertEqual(a1.round, r)
        self.assertEqual(a2.round, r)
        self.assertEqual(q.round, r)
        self.assertTrue(a1.problem_instance is None)
        self.assertTrue(a2.problem_instance is None)
        self.assertTrue(q.problem_instance is None)
        # Change q to problem question
        change_category(q, 'p_%d' % pi.id)
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.assertEqual(a1.problem_instance, pi)
        self.assertEqual(a2.problem_instance, pi)
        self.assertEqual(q.problem_instance, pi)
        self.assertEqual(a1.round, pi.round)
        self.assertEqual(a2.round, pi.round)
        self.assertEqual(q.round, pi.round)

    def test_change_denied(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        msg = Message.objects.filter(author__username='test_admin')[0]
        url = reverse('oioioiadmin:questions_message_change', args=(msg.id,))
        check_not_accessible(self, url)

    def test_reply_templates(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        url1 = reverse('get_reply_templates', kwargs={'contest_id': contest.id})
        response = self.client.get(url1)
        templates = response.json()
        self.assertEqual(templates[0]['name'], "N/A")
        self.assertEqual(templates[0]['content'], "No answer.")
        self.assertEqual(templates[3]['name'], "What contest is this?")
        self.assertEqual(len(templates), 4)
        url_inc = reverse(
            'increment_template_usage',
            kwargs={'contest_id': contest.id, 'template_id': 4},
        )
        for _i in range(12):
            response = self.client.get(url_inc)
        response = self.client.get(url1)
        templates = response.json()
        self.assertEqual(templates[0]['name'], "What contest is this?")
        self.assertEqual(len(templates), 4)
        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url1)

    def test_check_new_messages(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('check_new_messages', kwargs={'contest_id': 'c', 'topic_id': 2})
        resp = self.client.get(url, {'timestamp': 1347000000})
        data = resp.json()['messages']

        self.assertEqual(data[1][0], u'private-answer')

    def test_message_type_filter(self):
        contest = Contest.objects.get()
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})

        # Admin and regular users have slightly different filter forms,
        # so let's test both types of users.
        for username in ['test_user', 'test_admin']:
            self.assertTrue(self.client.login(username=username))
            response = self.client.get(
                url, {'message_type': FilterMessageForm.TYPE_ALL_MESSAGES}
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'private-answer')
            self.assertContains(response, 'public-answer')

            response = self.client.get(
                url, {'message_type': FilterMessageForm.TYPE_PUBLIC_ANNOUNCEMENTS}
            )
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'private-answer')
            self.assertContains(response, 'public-answer')

    def test_candidate_notifications(self):
        timestamp = datetime(2000, 9, 7, 13, 40, 0, tzinfo=timezone.utc)
        self.assertEqual(len(candidate_messages(timestamp)), 5)
        timestamp = datetime(2015, 9, 7, 13, 40, 0, tzinfo=timezone.utc)
        self.assertEqual(len(candidate_messages(timestamp)), 10)

    def test_unescaped(self):
        message = Message.objects.get(pk=10)
        mailnotify(message)
        m = mail.outbox[0]
        self.assertIn(">", m.subject)
        self.assertIn("& <> !! #$*&$!#", m.body)

    def test_mailnotify(self):
        def assertMessageId(id, body):
            self.assertIn("/questions/{}/".format(id), body)

        # Notify about a private message
        message = Message.objects.get(pk=3)
        mailnotify(message)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertIn("[OIOIOI][Test contest]", m.subject)
        self.assertEqual("test_user@example.com", m.to[0])
        self.assertIn("A new message has just appeared", m.body)
        self.assertIn("private-answer-body", m.body)
        # Private answer, the user has access to the top reference, so they
        # should receive it in the e-mail
        assertMessageId(message.top_reference.id, m.body)

        # Do not notify about a question
        question = Message.objects.get(pk=2)
        mailnotify(question)
        self.assertEqual(len(mail.outbox), 1)

        # Do not notify again about the same question
        with self.assertRaises(AssertionError):
            mailnotify(message)

        # Notify two users about a public message
        pubmsg = Message.objects.get(pk=4)
        mailnotify(pubmsg)
        self.assertEqual(len(mail.outbox), 3)
        m = mail.outbox[1]
        mm = mail.outbox[2]
        self.assertIn("[OIOIOI][Test contest]", m.subject)
        self.assertEqual("test_user@example.com", m.to[0])
        self.assertEqual("test_user2@example.com", mm.to[0])
        self.assertIn("A new message has just appeared", m.body)
        self.assertIn("public-answer-body", m.body)
        self.assertIn("A new message has just appeared", mm.body)
        self.assertIn("public-answer-body", mm.body)
        self.assertEqual(m.subject, mm.subject)
        # the author should receive the link to the top_reference
        # and the original question
        assertMessageId(pubmsg.top_reference.id, m.body)
        self.assertIn("question-body", m.body)
        # the non-author should receive the link to the answer
        # and should not receive the original question
        assertMessageId(pubmsg.id, mm.body)
        self.assertNotIn("question-body", mm.body)

    def test_unseen_mail_notifications(self):
        """Test whether the notifications are correctly *not* sent for messages
        which are not visible to the user"""
        mock_name = 'oioioi.questions.management.commands.mailnotifyd.visible_messages'
        with mock.patch(mock_name, return_value=Message.objects.none()):
            message = Message.objects.get(pk=4)
            mailnotify(message)
            self.assertEqual(len(mail.outbox), 0)


class TestAllMessagesView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
        'test_second_user_messages',
    ]

    def test_visible_messages(self):
        contest = Contest.objects.get()
        url = reverse('contest_all_messages', kwargs={'contest_id': contest.id})

        visible_to_user = [
            'general-question',
            'problem-question',
            'question-body',
            'private-answer-body',
            'public-answer-body',
            'user2-public-answer-body',
        ]
        hidden_to_user = [
            'user2-answered-question',
            'user2-unanswered-question',
            'user2-question-body',
            'user2-private-answer-body',
        ]
        # Note: reply topics are not displayed and regular users can not see
        #       questions of another users, so they can see reply as a single
        #       message with its topic.
        visible_for_non_admins = [
            'user2-public-answer-topic',
        ]
        hidden_to_all = [
            'user2-private-answer-topic',
        ]

        test_data = [
            {
                'username': 'test_user',
                'visible': visible_to_user + visible_for_non_admins,
                'hidden': hidden_to_user + hidden_to_all,
            },
            {
                'username': 'test_admin',
                'visible': visible_to_user + hidden_to_user,
                'hidden': visible_for_non_admins + hidden_to_all,
            },
        ]

        for d in test_data:
            self.assertTrue(self.client.login(username=d['username']))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for content in d['visible']:
                self.assertContains(response, content)
            for content in d['hidden']:
                self.assertNotContains(response, content)

    def test_marking_as_read(self):
        contest = Contest.objects.get()
        url = reverse('contest_all_messages', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NEW')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'NEW')

    def test_marking_as_needs_reply(self):
        contest = Contest.objects.get()
        url = reverse('contest_all_messages', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        unanswered = unanswered_questions(Message.objects.all())
        # We need additional modules like django-webtest or beuatiful soup
        # to gracefully inspect HTML instead of template context
        for entry in response.context['tree_list']:
            self.assertEqual(entry['needs_reply'], entry['message'] in unanswered)

    def test_messages_ordering(self):
        contest = Contest.objects.get()
        url = reverse('contest_all_messages', kwargs={'contest_id': contest.id})

        test_data = [
            {
                'username': 'test_user',
                'sort_key': lambda x: (
                    x['has_new_message'],
                    x['needs_reply'],
                    x['timestamp'],
                ),
                'visit_messages': [2, 7],
            },
            {
                'username': 'test_admin',
                'sort_key': lambda x: (
                    x['needs_reply'],
                    x['has_new_message'],
                    x['timestamp'],
                ),
                'visit_messages': [2, 7],
            },
        ]

        for d in test_data:
            self.assertTrue(self.client.login(username=d['username']))
            for mid in d['visit_messages']:
                url_visit = reverse(
                    'message_visit',
                    kwargs={'contest_id': contest.id, 'message_id': mid},
                )
                response = self.client.get(url_visit)
                self.assertEqual(response.status_code, 201)

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

            # We need additional modules like django-webtest or beuatiful soup
            # to gracefully inspect HTML instead of template context
            correct_tree_list = deepcopy(response.context['tree_list'])
            correct_tree_list.sort(key=d['sort_key'], reverse=True)
            for entry in correct_tree_list:
                entry['replies'].sort(key=d['sort_key'], reverse=True)

            self.assertEqual(response.context['tree_list'], correct_tree_list)

    def test_filter_presence(self):
        # Note: already tested in TestQuestions. Here, we are only testing
        #       if filter form is supported in this view.
        contest = Contest.objects.get()
        url = reverse('contest_all_messages', kwargs={'contest_id': contest.id})

        # Admin and regular users have slightly different filter forms,
        # so let's test both types of users.
        for username in ['test_user', 'test_admin']:
            self.assertTrue(self.client.login(username=username))
            response = self.client.get(
                url, {'message_type': FilterMessageForm.TYPE_ALL_MESSAGES}
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'private-answer')
            self.assertContains(response, 'public-answer')

            response = self.client.get(
                url, {'message_type': FilterMessageForm.TYPE_PUBLIC_ANNOUNCEMENTS}
            )
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'private-answer')
            self.assertContains(response, 'public-answer')


class TestUserInfo(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
        'test_templates',
    ]

    def test_user_info_page(self):
        contest = Contest.objects.get()
        user = User.objects.get(pk=1001)
        url = reverse(
            'user_info', kwargs={'contest_id': contest.id, 'user_id': user.id}
        )

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertContains(response, 'User info')
        self.assertContains(response, "User's messages")
        self.assertContains(response, 'general-question')
