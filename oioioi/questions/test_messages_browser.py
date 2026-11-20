from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from oioioi.base.tests import BrowserTestCase
from oioioi.contests.models import Contest
from oioioi.questions.models import Message, ReplyTemplate


class TestMessagePageScripts(BrowserTestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_messages",
        "test_permissions",
    ]

    def _open_message(self):
        context = self.new_browser_context("test_admin")
        page = context.new_page()
        page.goto(self.live_server_url + "/c/c/questions/2/")
        return context, page

    def test_reply_templates_are_shown_as_text(self):
        ReplyTemplate.objects.create(contest=Contest.objects.get(), name="<b>name</b>", content='<i>"content"</i>')
        context, page = self._open_message()
        try:
            link = page.locator("a.include-reply-template")
            link.wait_for(state="attached")
            # The templates are in a dropdown menu, hidden until it is opened.
            page.locator(".include-template .dropdown-toggle").click()
            link.wait_for()
            self.assertEqual(link.inner_text(), "<b>name</b>")
            self.assertEqual(link.get_attribute("title"), '<i>"content"</i>')
            self.assertEqual(page.locator(".template-replies b").count(), 0)

            link.click()
            self.assertTrue(page.locator("textarea#id_content").input_value().endswith('<i>"content"</i>'))
        finally:
            context.close()

    def test_new_answer_alert_is_shown_as_text(self):
        context, page = self._open_message()
        try:
            page.wait_for_function("typeof newAnswersConfig !== 'undefined' && newAnswersConfig.url")
            with self.server_lock:
                answer = Message.objects.create(
                    contest=Contest.objects.get(),
                    top_reference=Message.objects.get(pk=2),
                    kind="PUBLIC",
                    author=User.objects.get(username="test_contest_basicadmin"),
                    topic="t",
                    content="<b>answer</b> $1",
                    date=timezone.now() + timedelta(seconds=5),
                )
            body = page.locator(f"#alert_{answer.id} .oioioi-message__body")
            body.wait_for(timeout=15000)
            self.assertEqual(body.inner_text(), "<b>answer</b> $1")
            self.assertEqual(page.locator("#alerts b").count(), 0)

            page.locator(f"#alert_{answer.id} button", has_text="Dismiss").click()
            page.locator(f"#alert_{answer.id}").wait_for(state="hidden")
        finally:
            context.close()
