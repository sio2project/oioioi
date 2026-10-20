from copy import deepcopy
from datetime import UTC, datetime, timedelta  # pylint: disable=E0611

try:
    from unittest import mock
except ImportError:
    from unittest import mock
from django.contrib.auth.models import User
from django.core import mail
from django.test import RequestFactory
from django.urls import reverse

from oioioi.base.notification import NotificationHandler
from oioioi.base.tests import TestCase, check_not_accessible, fake_time
from oioioi.base.tests.tests import TestPublicMessage
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.participants.models import Participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.questions.forms import FilterMessageForm
from oioioi.questions.management.commands.mailnotifyd import (
    candidate_messages,
    mailnotify,
)
from oioioi.questions.models import AddQuestionMessage, Message, NewsMessage, QuestionSubscription, ReplyTemplate
from oioioi.questions.utils import unanswered_questions
from oioioi.usergroups.models import UserGroup

from .views import visible_messages


class TestContestControllerMixin:
    def users_to_receive_public_message_notification(self):
        return self.registration_controller().filter_participants(User.objects.all())


ProgrammingContestController.mix_in(TestContestControllerMixin)


class TestQuestions(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_messages",
        "test_templates",
        "test_subscriptions",
    ]

    def test_visibility(self):
        contest = Contest.objects.get()
        all_messages = [
            "problem-question",
            "contest-question",
            "public-answer",
            "private-answer",
        ]
        url = reverse("contest_messages", kwargs={"contest_id": contest.id})

        def check_visibility(*should_be_visible):
            response = self.client.get(url)
            for m in all_messages:
                if m in should_be_visible:
                    self.assertContains(response, m)
                else:
                    self.assertNotContains(response, m)

        self.assertTrue(self.client.login(username="test_user"))
        check_visibility("public-answer", "private-answer")
        self.assertTrue(self.client.login(username="test_user2"))
        check_visibility("public-answer")
        self.assertTrue(self.client.login(username="test_admin"))
        check_visibility("public-answer", "private-answer")

    def test_pub_date(self):
        contest = Contest.objects.get()
        all_messages = [
            "question-visible-title",
            "question-hidden1-title",
            "question-hidden2-title",
            "response-hidden-title",
            "visible-response-to-hidden",
        ]
        url = reverse("contest_messages", kwargs={"contest_id": contest.id})
        timestamp = datetime(2013, 9, 7, 13, 40, 0, tzinfo=UTC)

        def check_visibility(*should_be_visible):
            with fake_time(timestamp):
                response = self.client.get(url)
            for m in all_messages:
                if m in should_be_visible:
                    self.assertContains(response, m)
                else:
                    self.assertNotContains(response, m)

        self.assertTrue(self.client.login(username="test_user"))
        check_visibility("question-visible-title")
        self.assertTrue(self.client.login(username="test_admin"))
        check_visibility(
            "response-hidden-title",
            "question-hidden1-title",
            "visible-response-to-hidden",
        )

    def test_user_date(self):
        ta = datetime(1970, 1, 1, 12, 30, tzinfo=UTC)
        tb = datetime(1970, 1, 1, 13, 30, tzinfo=UTC)
        self.assertEqual(Message(date=ta, pub_date=None).get_user_date(), ta)
        self.assertEqual(Message(date=ta, pub_date=tb).get_user_date(), tb)

    def test_visible_messages(self):
        contest = Contest.objects.get()
        timestamp = datetime(2013, 9, 7, 13, 40, 0, tzinfo=UTC)

        def make_request(username):
            request = RequestFactory().request()
            request.timestamp = timestamp
            request.contest = contest
            request.user = User.objects.get(username=username)
            return request

        self.assertListEqual([5, 4, 3, 2, 1], [m.id for m in visible_messages(make_request("test_user"))])
        self.assertListEqual([5, 4], [m.id for m in visible_messages(make_request("test_user2"))])
        self.assertListEqual(
            [9, 8, 7, 6, 5, 4, 10, 3, 2, 1],
            [m.id for m in visible_messages(make_request("test_admin"))],
        )

    def test_new_labels(self):
        self.assertTrue(self.client.login(username="test_user"))
        contest = Contest.objects.get()
        list_url = reverse("contest_messages", kwargs={"contest_id": contest.id})
        timestamp = datetime.fromtimestamp(1347025200, tz=UTC)
        with fake_time(timestamp):
            response = self.client.get(list_url)
        self.assertContains(response, ">NEW<", count=2)
        public_answer = Message.objects.get(topic="public-answer")
        with fake_time(timestamp):
            response = self.client.get(
                reverse(
                    "message",
                    kwargs={"contest_id": contest.id, "message_id": public_answer.id},
                )
            )
        self.assertContains(response, "public-answer-body")
        self.assertNotContains(response, "contest-question")
        self.assertNotContains(response, "problem-question")
        with fake_time(timestamp):
            response = self.client.get(list_url)
        self.assertContains(response, ">NEW<", count=1)

    def check_unread_num(self, num):
        self.assertEqual(num, len(unanswered_questions(Message.objects.all())))

    def mark_read(self, message_id):
        contest = Message.objects.get(id=message_id).contest
        url_kwargs = {"contest_id": contest.id, "message_id": message_id}
        read_url = reverse("mark_question_read", kwargs=url_kwargs)
        response = self.client.post(read_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Success!")
        self.assertContains(response, "Mark unread")
        self.assertContains(response, "Marked read by")

    def mark_unread(self, message_id):
        contest = Message.objects.get(id=message_id).contest
        url_kwargs = {"contest_id": contest.id, "message_id": message_id}
        unread_url = reverse("mark_question_unread", kwargs=url_kwargs)
        response = self.client.post(unread_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Success!")
        self.assertContains(response, "Mark read")
        self.assertNotContains(response, "Marked read by")

    def test_mark_read(self):
        self.assertTrue(self.client.login(username="test_admin"))
        contest = Contest.objects.get()
        url_kwargs = {"contest_id": contest.id, "message_id": 1}
        message_url = reverse("message", kwargs=url_kwargs)
        read_url = reverse("mark_question_read", kwargs=url_kwargs)
        unread_url = reverse("mark_question_unread", kwargs=url_kwargs)
        # View the message
        self.check_unread_num(1)
        response = self.client.get(message_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mark read")

        # Mark the message as read
        self.mark_read(1)
        self.check_unread_num(0)
        # Try to mark it again
        response = self.client.post(read_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.check_unread_num(0)
        self.assertContains(response, "This question has already been marked read!")

        # Unmark the message
        self.mark_unread(1)
        self.check_unread_num(1)
        # Try to unmark it again
        response = self.client.post(unread_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.check_unread_num(1)
        self.assertContains(response, "This question has already been marked unread!")

        # You should be able to mark an answered message as read
        url_kwargs["message_id"] = 2
        message_url = reverse("message", kwargs=url_kwargs)
        response = self.client.get(message_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mark read")
        self.mark_read(2)
        self.mark_unread(2)

        # Only questions should be markable as read
        for i in (5, 6):
            url_kwargs["message_id"] = i
            message_url = reverse("message", kwargs=url_kwargs)
            response = self.client.get(message_url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Mark read")

    def test_ask_and_reply(self):
        self.assertTrue(self.client.login(username="test_user2"))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse("add_contest_message", kwargs={"contest_id": contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertEqual(len(form.fields["category"].choices) - 1, 2)

        post_data = {
            "category": f"p_{pi.id}",
            "topic": "the-new-question",
            "content": "the-new-body",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic="the-new-question")
        self.assertEqual(new_question.content, "the-new-body")
        self.assertEqual(new_question.kind, "QUESTION")
        self.assertIsNone(new_question.top_reference)
        self.assertEqual(new_question.contest, contest)
        self.assertEqual(new_question.problem_instance, pi)
        self.assertEqual(new_question.author.username, "test_user2")

        self.assertTrue(self.client.login(username="test_admin"))
        list_url = reverse("contest_messages", kwargs={"contest_id": contest.id})
        response = self.client.get(list_url)
        self.assertContains(response, "the-new-question")

        url = reverse("message", kwargs={"contest_id": contest.id, "message_id": new_question.id})
        response = self.client.get(url)
        self.assertIn("form", response.context)

        post_data = {
            "kind": "PUBLIC",
            "topic": "re-new-question",
            "content": "re-new-body",
            "save_template": True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        post_data = {
            "kind": "PUBLIC",
            "topic": "another-re-new-question",
            "content": "another-re-new-body",
            "save_template": False,
        }
        response = self.client.post(url, post_data)
        self.assertRaises(
            ReplyTemplate.DoesNotExist,
            lambda: ReplyTemplate.objects.get(content="another-re-new-body"),
        )
        self.assertEqual(response.status_code, 302)
        new_reply = Message.objects.get(topic="re-new-question")
        self.assertEqual(new_reply.content, "re-new-body")
        self.assertEqual(new_reply.kind, "PUBLIC")
        self.assertEqual(new_reply.top_reference, new_question)
        self.assertEqual(new_reply.contest, contest)
        self.assertEqual(new_reply.problem_instance, pi)
        self.assertEqual(new_reply.author.username, "test_admin")

        self.assertTrue(self.client.login(username="test_user"))
        q_url = reverse("message", kwargs={"contest_id": contest.id, "message_id": new_question.id})
        check_not_accessible(self, q_url)
        repl_url = reverse("message", kwargs={"contest_id": contest.id, "message_id": new_reply.id})
        response = self.client.get(repl_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "re-new-question")
        self.assertContains(response, "re-new-body")
        self.assertNotContains(response, "the-new-question")
        self.assertNotContains(response, "the-new-body")
        response = self.client.get(list_url)
        self.assertContains(response, repl_url)
        self.assertContains(response, "re-new-question")
        self.assertNotContains(response, "the-new-question")

        self.assertTrue(self.client.login(username="test_user2"))
        response = self.client.get(q_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "the-new-question")
        self.assertContains(response, "the-new-body")
        self.assertContains(response, "re-new-body")
        response = self.client.get(list_url)
        self.assertContains(response, q_url)
        self.assertContains(response, "re-new-question")
        self.assertNotContains(response, "the-new-question")

    def test_reply_notification(self):
        flags = {}
        flags["user_1001_got_notification"] = False
        flags["user_1002_got_notification"] = False

        @classmethod
        def fake_send_notification(
            cls,
            user,
            notification_type,
            notification_message,
            notificaion_message_arguments,
        ):
            if user.pk == 1002:
                flags["user_1002_got_notification"] = True
            if user.pk == 1001:
                flags["user_1001_got_notification"] = True

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        # Test user asks a new question
        self.assertTrue(self.client.login(username="test_user2"))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse("add_contest_message", kwargs={"contest_id": contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            "category": f"p_{pi.id}",
            "topic": "the-new-question",
            "content": "the-new-body",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic="the-new-question")

        # Test admin replies his question
        self.assertTrue(self.client.login(username="test_admin"))
        list_url = reverse("contest_messages", kwargs={"contest_id": contest.id})
        response = self.client.get(list_url)
        self.assertContains(response, "the-new-question")

        url = reverse("message", kwargs={"contest_id": contest.id, "message_id": new_question.id})
        response = self.client.get(url)
        self.assertIn("form", response.context)

        post_data = {
            "kind": "PRIVATE",
            "topic": "re-new-question",
            "content": "re-new-body",
            "save_template": True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        # Check if a notification for user was send
        self.assertTrue(flags["user_1002_got_notification"])
        self.assertFalse(flags["user_1001_got_notification"])

        NotificationHandler.send_notification = send_notification_backup

    def test_public_message_notification(self):
        flags = {}
        flags["user_1001_got_notification"] = False
        flags["user_1002_got_notification"] = False

        @classmethod
        def fake_send_notification(
            cls,
            user,
            notification_type,
            notification_message,
            notificaion_message_arguments,
        ):
            if user.pk == 1002:
                flags["user_1002_got_notification"] = True
            if user.pk == 1001:
                flags["user_1001_got_notification"] = True

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        # Test user asks a new question
        self.assertTrue(self.client.login(username="test_user2"))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()

        url = reverse("add_contest_message", kwargs={"contest_id": contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            "category": f"p_{pi.id}",
            "topic": "the-new-question",
            "content": "the-new-body",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic="the-new-question")

        # Test admin replies his question
        self.assertTrue(self.client.login(username="test_admin"))
        list_url = reverse("contest_messages", kwargs={"contest_id": contest.id})
        response = self.client.get(list_url)
        self.assertContains(response, "the-new-question")

        url = reverse("message", kwargs={"contest_id": contest.id, "message_id": new_question.id})
        response = self.client.get(url)
        self.assertIn("form", response.context)

        post_data = {
            "kind": "PUBLIC",
            "topic": "re-new-question",
            "content": "re-new-body",
            "save_template": True,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(flags["user_1002_got_notification"])
        self.assertTrue(flags["user_1001_got_notification"])

        NotificationHandler.send_notification = send_notification_backup

    def test_filtering(self):
        self.assertTrue(self.client.login(username="test_admin"))
        contest = Contest.objects.get()
        url = reverse("contest_messages", kwargs={"contest_id": contest.id})

        get_data = {"author": "test_admin"}
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "general-question")
        self.assertNotContains(response, "problem-question")
        self.assertContains(response, "public-answer")
        self.assertContains(response, "private-answer")

        get_data["author"] = "test_user"
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "general-question")
        self.assertContains(response, "problem-question")
        self.assertNotContains(response, "public-answer")
        self.assertNotContains(response, "private-answer")

        get_data["category"] = "r_1"
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "general-question")
        self.assertNotContains(response, "problem-question")
        self.assertNotContains(response, "public-answer")
        self.assertNotContains(response, "private-answer")

        get_data["category"] = "p_1"
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "general-question")
        self.assertContains(response, "problem-question")
        self.assertNotContains(response, "public-answer")
        self.assertNotContains(response, "private-answer")

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "general-question")
        self.assertNotContains(response, "problem-question")
        self.assertNotContains(response, "public-answer")
        self.assertContains(response, "private-answer")

    def test_authors_list(self):
        self.assertTrue(self.client.login(username="test_admin"))
        contest = Contest.objects.get()
        url = reverse("get_messages_authors", kwargs={"contest_id": contest.id})
        response = self.client.get(url, {"substr": ""})
        self.assertEqual(404, response.status_code)
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)

        response = self.client.get(url, {"substr": "te"})
        self.assertEqual(200, response.status_code)
        response = response.json()
        self.assertListEqual(["test_admin (Test Admin)", "test_user (Test User)"], response)

        response = self.client.get(url, {"substr": "test admin"})
        response = response.json()
        self.assertListEqual(["test_admin (Test Admin)"], response)

        self.assertTrue(self.client.login(username="test_user"))
        check_not_accessible(self, url)

    def test_change_category(self):
        pi = ProblemInstance.objects.get()
        r = pi.round
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.client.get("/c/c/")  # 'c' becomes the current contest

        def change_category(msg, cat):
            url = reverse("oioioiadmin:questions_message_change", args=(msg.id,))
            self.assertTrue(self.client.login(username="test_admin"))
            response = self.client.get(url)
            self.assertIn("form", response.context)

            post_data = {
                "kind": msg.kind,
                "category": cat,
                "topic": msg.topic,
                "content": msg.content,
            }
            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 302)

        # Change a1 to round question
        change_category(a1, f"r_{r.id}")
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.assertEqual(a1.round, r)
        self.assertEqual(a2.round, r)
        self.assertEqual(q.round, r)
        self.assertTrue(a1.problem_instance is None)
        self.assertTrue(a2.problem_instance is None)
        self.assertTrue(q.problem_instance is None)
        # Change q to problem question
        change_category(q, f"p_{pi.id}")
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.assertEqual(a1.problem_instance, pi)
        self.assertEqual(a2.problem_instance, pi)
        self.assertEqual(q.problem_instance, pi)
        self.assertEqual(a1.round, pi.round)
        self.assertEqual(a2.round, pi.round)
        self.assertEqual(q.round, pi.round)

    def test_change_denied(self):
        self.assertTrue(self.client.login(username="test_user"))
        self.client.get("/c/c/")  # 'c' becomes the current contest

        msg = Message.objects.filter(author__username="test_admin")[0]
        url = reverse("oioioiadmin:questions_message_change", args=(msg.id,))
        check_not_accessible(self, url)

    def test_reply_templates(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username="test_admin"))
        url1 = reverse("get_reply_templates", kwargs={"contest_id": contest.id})
        response = self.client.get(url1)
        templates = response.json()
        self.assertEqual(templates[0]["name"], "N/A")
        self.assertEqual(templates[0]["content"], "No answer.")
        self.assertEqual(templates[3]["name"], "What contest is this?")
        self.assertEqual(len(templates), 4)
        url_inc = reverse(
            "increment_template_usage",
            kwargs={"contest_id": contest.id, "template_id": 4},
        )
        for _i in range(12):
            response = self.client.get(url_inc)
        response = self.client.get(url1)
        templates = response.json()
        self.assertEqual(templates[0]["name"], "What contest is this?")
        self.assertEqual(len(templates), 4)
        self.assertTrue(self.client.login(username="test_user"))
        check_not_accessible(self, url1)

    def test_check_new_messages(self):
        self.assertTrue(self.client.login(username="test_user"))
        url = reverse("check_new_messages", kwargs={"contest_id": "c", "topic_id": 2})
        resp = self.client.get(url, {"timestamp": 1347000000})
        data = resp.json()["messages"]

        self.assertEqual(data[1][0], "private-answer")

    def test_message_type_filter(self):
        contest = Contest.objects.get()
        url = reverse("contest_messages", kwargs={"contest_id": contest.id})

        # Admin and regular users have slightly different filter forms,
        # so let's test both types of users.
        for username in ["test_user", "test_admin"]:
            self.assertTrue(self.client.login(username=username))
            response = self.client.get(url, {"message_type": FilterMessageForm.TYPE_ALL_MESSAGES})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "private-answer")
            self.assertContains(response, "public-answer")

            response = self.client.get(url, {"message_type": FilterMessageForm.TYPE_PUBLIC_ANNOUNCEMENTS})
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "private-answer")
            self.assertContains(response, "public-answer")

    def test_candidate_notifications(self):
        timestamp = datetime(2000, 9, 7, 13, 40, 0, tzinfo=UTC)
        self.assertEqual(len(candidate_messages(timestamp)), 5)
        timestamp = datetime(2015, 9, 7, 13, 40, 0, tzinfo=UTC)
        self.assertEqual(len(candidate_messages(timestamp)), 10)

    def test_unescaped(self):
        message = Message.objects.get(pk=10)
        mailnotify(message)
        m = mail.outbox[0]
        self.assertIn(">", m.subject)
        self.assertIn("& <> !! #$*&$!#", m.body)

    def test_mailnotify(self):
        def assertMessageId(id, body):
            self.assertIn(f"/questions/{id}/", body)

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
        mock_name = "oioioi.questions.management.commands.mailnotifyd.visible_messages"
        with mock.patch(mock_name, return_value=Message.objects.none()):
            message = Message.objects.get(pk=4)
            mailnotify(message)
            self.assertEqual(len(mail.outbox), 0)


class TestPrivateMessages(TestCase):
    fixtures = ["test_users", "test_contest", "test_participant"]

    def setUp(self):
        super().setUp()
        self.contest = Contest.objects.get()
        self.admin = User.objects.get(username="test_admin")
        self.recipient_a = User.objects.get(username="test_user")
        self.recipient_b = User.objects.get(username="test_user2")
        self.inactive_participant = User.objects.get(username="test_user3")
        self.outsider = User.objects.get(username="test_admin2")
        self.other_participant = User.objects.create(username="other_participant")

        Participant.objects.create(contest=self.contest, user=self.recipient_b)
        Participant.objects.create(contest=self.contest, user=self.inactive_participant, status="BANNED")
        Participant.objects.create(contest=self.contest, user=self.other_participant)

        self.group = self._create_group("contest group", self.recipient_a, self.recipient_b, self.inactive_participant)

    def _create_group(self, name, *members):
        group = UserGroup.objects.create(name=name)
        group.owners.add(self.admin)
        group.members.add(*members)
        group.contests.add(self.contest)
        return group

    def _private_message_url(self):
        return reverse("add_private_message", kwargs={"contest_id": self.contest.id})

    def _private_message_data(self, topic, recipient=None, groups=(), pub_date=None):
        data = {
            "category": "r_1",
            "recipient": recipient.username if recipient else "",
            "groups": [group.id for group in groups],
            "topic": topic,
            "content": f"{topic}-body",
        }
        if pub_date is not None:
            data["pub_date"] = pub_date.strftime("%Y-%m-%d %H:%M:%S")
        return data

    def _send_private_message(self, topic, **kwargs):
        return self.client.post(self._private_message_url(), self._private_message_data(topic, **kwargs))

    def _edit_private_message(self, message, recipient=None, groups=()):
        self.client.get(f"/c/{self.contest.id}/")
        url = reverse("oioioiadmin:questions_message_change", args=(message.id,))
        data = self._private_message_data(message.topic, recipient=recipient, groups=groups, pub_date=message.pub_date)
        data["kind"] = "PRIVATE"
        return self.client.post(url, data)

    def _reply(self, username, url, topic):
        self.assertTrue(self.client.login(username=username))
        response = self.client.post(
            url,
            {
                "kind": "PRIVATE",
                "topic": topic,
                "content": f"{topic}-body",
                "save_template": False,
            },
        )
        self.assertEqual(response.status_code, 302)
        return Message.objects.get(topic=topic)

    def test_admin_can_send_private_message_to_participant(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(self._private_message_url())
        self.assertEqual(response.status_code, 200)

        response = self._send_private_message("private-message", recipient=self.recipient_a)
        self.assertEqual(response.status_code, 302)

        message = Message.objects.get(topic="private-message")
        self.assertEqual(message.author, self.admin)
        self.assertEqual(message.kind, "PRIVATE")
        self.assertIsNone(message.top_reference)
        self.assertEqual(message.contest, self.contest)
        self.assertQuerySetEqual(message.recipients.all(), [self.recipient_a])

    def test_only_admin_can_send_private_message(self):
        self.assertTrue(self.client.login(username="test_user"))
        check_not_accessible(self, self._private_message_url())
        response = self._send_private_message("forbidden-private-message", recipient=self.recipient_a)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Message.objects.filter(topic="forbidden-private-message").exists())

    def test_private_message_controls_are_only_available_to_admin(self):
        list_url = reverse("contest_messages", kwargs={"contest_id": self.contest.id})
        private_message_url = self._private_message_url()
        hints_url = reverse("get_private_message_recipients", kwargs={"contest_id": self.contest.id})
        preview_url = reverse("get_private_message_recipients_preview", kwargs={"contest_id": self.contest.id})

        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(list_url)
        self.assertContains(response, private_message_url)
        content = " ".join(response.content.decode().split())
        self.assertNotIn(
            f'<a role="button" class="btn btn-sm btn-outline-secondary" href="{private_message_url}">',
            content,
        )
        self.assertIn(
            f'<a class="btn btn-sm btn-outline-secondary" href="{private_message_url}">',
            content,
        )
        response = self.client.get(hints_url, {"substr": "test_user"})
        self.assertEqual(response.status_code, 200)
        hints = response.json()
        self.assertTrue(any(hint.startswith("test_user ") for hint in hints))
        self.assertTrue(any(hint.startswith("test_user2 ") for hint in hints))
        self.assertFalse(any(hint.startswith("test_user3 ") for hint in hints))
        response = self.client.get(preview_url, {"recipient": self.recipient_a.username, "groups[]": [self.group.id]})
        self.assertEqual([recipient["username"] for recipient in response.json()], ["test_user", "test_user2"])

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(list_url)
        self.assertNotContains(response, self._private_message_url())
        check_not_accessible(self, hints_url)
        check_not_accessible(self, preview_url)

    def test_private_message_recipient_descriptions_are_accessible(self):
        self.assertTrue(self.client.login(username="test_admin"))

        response = self.client.get(self._private_message_url())
        self.assertContains(response, 'id="private-message-recipients-label"')
        self.assertContains(response, 'aria-labelledby="private-message-recipients-label"')
        self.assertNotContains(response, '<label class="control-label">Recipients</label>', html=True)

        response = self._send_private_message(
            "scheduled-private-message",
            recipient=self.recipient_a,
            pub_date=datetime(2099, 1, 1, tzinfo=UTC),
        )
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="scheduled-private-message")

        self.client.get(f"/c/{self.contest.id}/")
        change_url = reverse("oioioiadmin:questions_message_change", args=(message.id,))
        response = self.client.get(change_url)
        self.assertContains(
            response,
            '<div class="control-label">Current recipients</div>',
            html=True,
        )
        self.assertNotContains(response, '<label class="control-label">Current recipients</label>', html=True)

    def test_groups_are_expanded_and_recipients_are_deduplicated(self):
        second_group = self._create_group("second contest group", self.recipient_b, self.other_participant, self.outsider)
        self.assertTrue(self.client.login(username="test_admin"))

        response = self._send_private_message("private-group-message", recipient=self.recipient_a, groups=(self.group, second_group))
        self.assertEqual(response.status_code, 302)

        message = Message.objects.get(topic="private-group-message")
        self.assertQuerySetEqual(message.recipients.order_by("username"), [self.other_participant, self.recipient_a, self.recipient_b])

    def test_recipient_must_be_active_participant(self):
        self.assertTrue(self.client.login(username="test_admin"))

        for recipient in (self.inactive_participant, self.outsider):
            topic = f"invalid-recipient-{recipient.username}"
            response = self._send_private_message(topic, recipient=recipient)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Message.objects.filter(topic=topic).exists())

    def test_group_must_be_attached_to_contest(self):
        other_group = UserGroup.objects.create(name="other contest group")
        other_group.owners.add(self.admin)
        other_group.members.add(self.recipient_a)
        self.assertTrue(self.client.login(username="test_admin"))

        response = self._send_private_message("other-group-message", groups=(other_group,))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Message.objects.filter(topic="other-group-message").exists())

    def test_private_message_form_without_usergroups(self):
        self.assertTrue(self.client.login(username="test_admin"))

        with self.modify_settings(INSTALLED_APPS={"remove": "oioioi.usergroups"}):
            response = self.client.get(self._private_message_url())
            self.assertNotContains(response, 'id="id_groups"')
            response = self._send_private_message("private-message", recipient=self.recipient_a)

        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="private-message")
        self.assertQuerySetEqual(message.recipients.all(), [self.recipient_a])

        self.client.get(f"/c/{self.contest.id}/")
        change_url = reverse("oioioiadmin:questions_message_change", args=(message.id,))
        with self.modify_settings(INSTALLED_APPS={"remove": "oioioi.usergroups"}):
            response = self.client.get(change_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="id_groups"')

    def test_recipients_do_not_make_other_message_kinds_visible(self):
        message = Message.objects.create(
            round=self.contest.round_set.get(),
            author=self.recipient_b,
            kind="QUESTION",
            topic="other-question",
            content="other-question-body",
        )
        message.recipients.add(self.recipient_a)

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(reverse("contest_messages", kwargs={"contest_id": self.contest.id}))
        self.assertNotContains(response, message.topic)

    def test_scheduled_message_is_hidden_until_publication(self):
        timestamp = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
        self.assertTrue(self.client.login(username="test_admin"))
        with mock.patch.object(NotificationHandler, "send_notification") as send_notification:
            with fake_time(timestamp):
                response = self._send_private_message("scheduled-private-message", recipient=self.recipient_a, pub_date=timestamp + timedelta(hours=1))
        send_notification.assert_not_called()
        self.assertEqual(response.status_code, 302)

        message = Message.objects.get(topic="scheduled-private-message")
        self.assertNotIn(message, candidate_messages(timestamp))
        message_url = reverse("message", kwargs={"contest_id": self.contest.id, "message_id": message.id})
        list_url = reverse("contest_messages", kwargs={"contest_id": self.contest.id})

        with fake_time(timestamp):
            response = self.client.get(message_url)
        self.assertIsNone(response.context["form"])

        self.assertTrue(self.client.login(username="test_user"))
        with fake_time(message.pub_date - timedelta(seconds=1)):
            response = self.client.get(list_url)
            self.assertNotContains(response, message.topic)
            check_not_accessible(self, message_url)
        with fake_time(message.pub_date):
            response = self.client.get(list_url)
            self.assertContains(response, message.topic)
            self.assertEqual(self.client.get(message_url).status_code, 200)

    def test_recipients_can_only_be_changed_before_publication(self):
        timestamp = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
        self.assertTrue(self.client.login(username="test_admin"))
        with fake_time(timestamp):
            response = self._send_private_message("editable-private-message", recipient=self.recipient_a, pub_date=timestamp + timedelta(hours=1))
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="editable-private-message")

        with fake_time(message.pub_date - timedelta(seconds=1)):
            response = self._edit_private_message(message, recipient=self.recipient_b)
        self.assertEqual(response.status_code, 302)
        message.refresh_from_db()
        self.assertQuerySetEqual(message.recipients.all(), [self.recipient_b])

        with fake_time(message.pub_date):
            response = self._edit_private_message(message, recipient=self.recipient_a)
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertQuerySetEqual(message.recipients.all(), [self.recipient_b])

    def test_immediate_message_recipients_cannot_be_changed(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("immediate-private-message", recipient=self.recipient_a)
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="immediate-private-message")

        response = self._edit_private_message(message, recipient=self.recipient_b)
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertQuerySetEqual(message.recipients.all(), [self.recipient_a])

    def test_group_members_are_snapshotted_on_each_explicit_save(self):
        timestamp = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
        self.assertTrue(self.client.login(username="test_admin"))
        with fake_time(timestamp):
            response = self._send_private_message("snapshotted-private-message", groups=(self.group,), pub_date=timestamp + timedelta(hours=1))
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="snapshotted-private-message")
        self.assertQuerySetEqual(message.recipients.order_by("username"), [self.recipient_a, self.recipient_b])

        self.group.members.remove(self.recipient_a)
        self.group.members.add(self.inactive_participant)
        participant = Participant.objects.get(contest=self.contest, user=self.inactive_participant)
        participant.status = "ACTIVE"
        participant.save()
        self.assertQuerySetEqual(message.recipients.order_by("username"), [self.recipient_a, self.recipient_b])

        with fake_time(message.pub_date - timedelta(seconds=1)):
            response = self._edit_private_message(message, groups=(self.group,))
        self.assertEqual(response.status_code, 302)
        message.refresh_from_db()
        self.assertQuerySetEqual(message.recipients.order_by("username"), [self.recipient_b, self.inactive_participant])

    def test_group_replies_create_separate_private_conversations(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("group-private-message", groups=(self.group,))
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="group-private-message")
        message_url = reverse("message", kwargs={"contest_id": self.contest.id, "message_id": message.id})

        reply_a = self._reply("test_user", message_url, "reply-a")
        admin_reply_a = self._reply("test_admin", reply_a.get_absolute_url(), "admin-reply-a")
        self._reply("test_user", message_url, "second-reply-a")
        self._reply("test_admin", admin_reply_a.get_absolute_url(), "second-admin-reply-a")
        reply_b = self._reply("test_user2", message_url, "reply-b")
        self._reply("test_admin", reply_b.get_absolute_url(), "admin-reply-b")

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(message_url)
        self.assertContains(response, "group-private-message-body")
        self.assertContains(response, "reply-a-body")
        self.assertContains(response, "admin-reply-a-body")
        self.assertContains(response, "second-reply-a-body")
        self.assertContains(response, "second-admin-reply-a-body")
        self.assertNotContains(response, "reply-b-body")
        self.assertNotContains(response, "admin-reply-b-body")
        check_not_accessible(self, reply_b.get_absolute_url())

        self.assertTrue(self.client.login(username="test_user2"))
        response = self.client.get(message_url)
        self.assertContains(response, "group-private-message-body")
        self.assertContains(response, "reply-b-body")
        self.assertContains(response, "admin-reply-b-body")
        self.assertNotContains(response, "reply-a-body")
        self.assertNotContains(response, "admin-reply-a-body")
        check_not_accessible(self, reply_a.get_absolute_url())

        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(reply_a.get_absolute_url())
        self.assertContains(response, "reply-a-body")
        self.assertContains(response, "admin-reply-a-body")
        self.assertNotContains(response, "reply-b-body")
        response = self.client.get(reply_b.get_absolute_url())
        self.assertContains(response, "reply-b-body")
        self.assertContains(response, "admin-reply-b-body")
        self.assertNotContains(response, "reply-a-body")

        self.assertTrue(self.client.login(username="other_participant"))
        check_not_accessible(self, message_url)

    def test_group_overview_does_not_display_a_user(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("group-private-message", groups=(self.group,))
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="group-private-message")

        response = self.client.get(message.get_absolute_url())
        self.assertNotContains(response, "Display user")

        conversation_url = reverse(
            "private_message",
            kwargs={
                "contest_id": self.contest.id,
                "message_id": message.id,
                "recipient_id": self.recipient_a.id,
            },
        )
        response = self.client.get(conversation_url)
        recipient_url = reverse(
            "user_info",
            kwargs={
                "contest_id": self.contest.id,
                "user_id": self.recipient_a.id,
            },
        )
        self.assertContains(response, "Display user")
        self.assertContains(response, recipient_url)
        self.assertNotContains(
            response,
            f'<a role="button" class="btn btn-sm btn-outline-secondary" href="{recipient_url}">',
        )
        self.assertContains(
            response,
            f'<a class="btn btn-sm btn-outline-secondary" href="{recipient_url}">',
        )

    def test_private_message_badges_use_bootstrap_text_background(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("private-message", recipient=self.recipient_a)
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="private-message")

        responses = [
            self.client.get(reverse("contest_messages", kwargs={"contest_id": self.contest.id})),
            self.client.get(message.get_absolute_url()),
        ]
        for response in responses:
            self.assertContains(response, "badge text-bg-light")
            self.assertNotContains(response, "badge-light")

    def test_participant_cannot_save_private_reply_as_template(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("private-message", recipient=self.recipient_a)
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="private-message")

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.post(
            message.get_absolute_url(),
            {
                "kind": "PRIVATE",
                "topic": "private-reply",
                "content": "private-reply-body",
                "save_template": True,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ReplyTemplate.objects.filter(content="private-reply-body").exists())

    def test_admin_can_start_an_individual_group_conversation(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("admin-started-message", groups=(self.group,))
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="admin-started-message")
        conversation_url = reverse(
            "private_message",
            kwargs={
                "contest_id": self.contest.id,
                "message_id": message.id,
                "recipient_id": self.recipient_a.id,
            },
        )

        response = self.client.get(message.get_absolute_url())
        self.assertContains(response, conversation_url)
        reply = self._reply("test_admin", conversation_url, "admin-started-reply")
        self.assertQuerySetEqual(reply.recipients.all(), [self.recipient_a])

        self.assertTrue(self.client.login(username="test_user"))
        self.assertContains(self.client.get(message.get_absolute_url()), "admin-started-reply-body")
        self.assertTrue(self.client.login(username="test_user2"))
        self.assertNotContains(self.client.get(message.get_absolute_url()), "admin-started-reply-body")

    def test_private_reply_cannot_be_changed_to_public(self):
        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("private-message", recipient=self.recipient_a)
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="private-message")
        reply = self._reply("test_user", message.get_absolute_url(), "private-reply")

        self.assertTrue(self.client.login(username="test_admin"))
        self.client.get(f"/c/{self.contest.id}/")
        url = reverse("oioioiadmin:questions_message_change", args=(reply.id,))
        response = self.client.post(
            url,
            {
                "category": "r_1",
                "kind": "PUBLIC",
                "topic": reply.topic,
                "content": reply.content,
                "pub_date": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        reply.refresh_from_db()
        self.assertEqual(reply.kind, "PRIVATE")

    def test_private_message_notifications_follow_the_conversation(self):
        for user in (self.admin, self.recipient_a, self.recipient_b):
            QuestionSubscription.objects.create(contest=self.contest, user=user)

        self.assertTrue(self.client.login(username="test_admin"))
        response = self._send_private_message("notification-message", groups=(self.group,))
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get(topic="notification-message")

        with mock.patch.object(NotificationHandler, "send_notification") as send_notification:
            mailnotify(message)
        self.assertEqual(sorted(email.to[0] for email in mail.outbox), ["test_user2@example.com", "test_user@example.com"])
        self.assertEqual(sorted(call.args[0].username for call in send_notification.call_args_list), ["test_user", "test_user2"])

        mail.outbox.clear()
        reply = self._reply("test_user", message.get_absolute_url(), "participant-reply")
        with mock.patch.object(NotificationHandler, "send_notification") as send_notification:
            mailnotify(reply)
        self.assertEqual([email.to[0] for email in mail.outbox], ["test_admin@example.com"])
        self.assertEqual([call.args[0] for call in send_notification.call_args_list], [self.admin])

        mail.outbox.clear()
        admin_reply = self._reply("test_admin", reply.get_absolute_url(), "admin-reply")
        with mock.patch.object(NotificationHandler, "send_notification") as send_notification:
            mailnotify(admin_reply)
        self.assertEqual([email.to[0] for email in mail.outbox], ["test_user@example.com"])
        self.assertEqual([call.args[0] for call in send_notification.call_args_list], [self.recipient_a])
        self.assertIn(admin_reply.get_absolute_url(), mail.outbox[0].body)


class TestAllMessagesView(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_messages",
        "test_second_user_messages",
    ]

    def test_visible_messages(self):
        contest = Contest.objects.get()
        url = reverse("contest_all_messages", kwargs={"contest_id": contest.id})

        visible_to_user = [
            "general-question",
            "problem-question",
            "question-body",
            "private-answer-body",
            "public-answer-body",
            "user2-public-answer-body",
        ]
        hidden_to_user = [
            "user2-answered-question",
            "user2-unanswered-question",
            "user2-question-body",
            "user2-private-answer-body",
        ]
        # Note: reply topics are not displayed and regular users can not see
        #       questions of another users, so they can see reply as a single
        #       message with its topic.
        visible_for_non_admins = [
            "user2-public-answer-topic",
        ]
        hidden_to_all = [
            "user2-private-answer-topic",
        ]

        test_data = [
            {
                "username": "test_user",
                "visible": visible_to_user + visible_for_non_admins,
                "hidden": hidden_to_user + hidden_to_all,
            },
            {
                "username": "test_admin",
                "visible": visible_to_user + hidden_to_user,
                "hidden": visible_for_non_admins + hidden_to_all,
            },
        ]

        for d in test_data:
            self.assertTrue(self.client.login(username=d["username"]))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            for content in d["visible"]:
                self.assertContains(response, content)
            for content in d["hidden"]:
                self.assertNotContains(response, content)

    def test_marking_as_read(self):
        contest = Contest.objects.get()
        url = reverse("contest_all_messages", kwargs={"contest_id": contest.id})

        self.assertTrue(self.client.login(username="test_user"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NEW")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "NEW")

    def test_marking_as_needs_reply(self):
        contest = Contest.objects.get()
        url = reverse("contest_all_messages", kwargs={"contest_id": contest.id})

        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        unanswered = unanswered_questions(Message.objects.all())
        # We need additional modules like django-webtest or beuatiful soup
        # to gracefully inspect HTML instead of template context
        for entry in response.context["tree_list"]:
            self.assertEqual(entry["needs_reply"], entry["message"] in unanswered)

    def test_messages_ordering(self):
        contest = Contest.objects.get()
        url = reverse("contest_all_messages", kwargs={"contest_id": contest.id})

        test_data = [
            {
                "username": "test_user",
                "sort_key": lambda x: (
                    x["has_new_message"],
                    x["needs_reply"],
                    x["timestamp"],
                ),
                "visit_messages": [2, 7],
            },
            {
                "username": "test_admin",
                "sort_key": lambda x: (
                    x["needs_reply"],
                    x["has_new_message"],
                    x["timestamp"],
                ),
                "visit_messages": [2, 7],
            },
        ]

        for d in test_data:
            self.assertTrue(self.client.login(username=d["username"]))
            for mid in d["visit_messages"]:
                url_visit = reverse(
                    "message_visit",
                    kwargs={"contest_id": contest.id, "message_id": mid},
                )
                response = self.client.get(url_visit)
                self.assertEqual(response.status_code, 201)

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

            # We need additional modules like django-webtest or beuatiful soup
            # to gracefully inspect HTML instead of template context
            correct_tree_list = deepcopy(response.context["tree_list"])
            correct_tree_list.sort(key=d["sort_key"], reverse=True)
            for entry in correct_tree_list:
                entry["replies"].sort(key=d["sort_key"], reverse=True)

            self.assertEqual(response.context["tree_list"], correct_tree_list)

    def test_filter_presence(self):
        # Note: already tested in TestQuestions. Here, we are only testing
        #       if filter form is supported in this view.
        contest = Contest.objects.get()
        url = reverse("contest_all_messages", kwargs={"contest_id": contest.id})

        # Admin and regular users have slightly different filter forms,
        # so let's test both types of users.
        for username in ["test_user", "test_admin"]:
            self.assertTrue(self.client.login(username=username))
            response = self.client.get(url, {"message_type": FilterMessageForm.TYPE_ALL_MESSAGES})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "private-answer")
            self.assertContains(response, "public-answer")

            response = self.client.get(url, {"message_type": FilterMessageForm.TYPE_PUBLIC_ANNOUNCEMENTS})
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "private-answer")
            self.assertContains(response, "public-answer")


class TestUserInfo(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_messages",
        "test_templates",
    ]

    def test_user_info_page(self):
        contest = Contest.objects.get()
        user = User.objects.get(pk=1001)
        url = reverse("user_info", kwargs={"contest_id": contest.id, "user_id": user.id})

        self.assertTrue(self.client.login(username="test_admin"))
        response = self.client.get(url)
        self.assertContains(response, "User info")
        self.assertContains(response, "User's messages")
        self.assertContains(response, "general-question")


class PublicMessageContestController(ProgrammingContestController):
    questions_news_message = "Test public message"
    add_question_message = "Test public message"


class TestNewsMessage(TestPublicMessage):
    model = NewsMessage
    button_viewname = "contest_messages"
    edit_viewname = "edit_question_news_message"
    viewname = "contest_messages"
    controller_name = "oioioi.questions.tests.PublicMessageContestController"


class TestAddQuestionMessage(TestPublicMessage):
    model = AddQuestionMessage
    button_viewname = "contest_messages"
    edit_viewname = "edit_add_question_message"
    viewname = "add_contest_message"
    controller_name = "oioioi.questions.tests.PublicMessageContestController"
