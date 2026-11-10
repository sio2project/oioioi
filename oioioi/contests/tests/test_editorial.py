from datetime import timedelta

from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from oioioi.base.tests import TestCase
from oioioi.contests.models import ProblemInstance
from oioioi.problems.models import Problem, ProblemAttachment


class TestEditorialView(TestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_permissions",
    ]

    def setUp(self):
        super().setUp()
        self.problem = Problem.objects.get()
        self.problem_instance = ProblemInstance.objects.get(problem=self.problem)
        self.problem_instance.can_access_editorial = True
        self.problem_instance.save()
        self.client.login(username="test_user")

    def test_file_editorial(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="file-editorial",
            content=ContentFile(b"file content", name="editorial.pdf"),
            is_editorial=True,
        )
        pa.save()

        url = reverse("editorial", kwargs={"contest_id": self.problem_instance.contest.id, "problem_instance": self.problem_instance.short_name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"file content")

    def test_url_editorial(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="url-editorial",
            url="https://youtube.com/watch?v=123",
            is_editorial=True,
        )
        pa.save()

        url = reverse("editorial", kwargs={"contest_id": self.problem_instance.contest.id, "problem_instance": self.problem_instance.short_name})
        response = self.client.get(url)
        self.assertRedirects(response, "https://youtube.com/watch?v=123", fetch_redirect_response=False)

    def test_no_editorial(self):
        url = reverse("editorial", kwargs={"contest_id": self.problem_instance.contest.id, "problem_instance": self.problem_instance.short_name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"editorial is not available", response.content)

    def _file_editorial(self, **kwargs):
        return ProblemAttachment.objects.create(
            problem=self.problem,
            description="file-editorial",
            content=ContentFile(b"file content", name="editorial.pdf"),
            is_editorial=True,
            **kwargs,
        )

    def _attachment_url(self, attachment):
        return reverse("problem_attachment", kwargs={"contest_id": self.problem_instance.contest.id, "attachment_id": attachment.id})

    def test_editorial_hidden_for_problem_instance(self):
        attachment = self._file_editorial()
        self.problem_instance.can_access_editorial = False
        self.problem_instance.save()

        url = reverse("editorial", kwargs={"contest_id": self.problem_instance.contest.id, "problem_instance": self.problem_instance.short_name})
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(self._attachment_url(attachment)).status_code, 403)

    def test_attachment_view_respects_pub_date(self):
        future = self._file_editorial(pub_date=timezone.now() + timedelta(days=1))
        self.assertEqual(self.client.get(self._attachment_url(future)).status_code, 403)

        past = self._file_editorial(pub_date=timezone.now() - timedelta(days=1))
        response = self.client.get(self._attachment_url(past))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"file content")

    def test_future_pub_date(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="future-editorial",
            url="https://youtube.com/watch?v=123",
            is_editorial=True,
            pub_date=timezone.now() + timedelta(days=1),
        )
        pa.save()

        url = reverse("editorial", kwargs={"contest_id": self.problem_instance.contest.id, "problem_instance": self.problem_instance.short_name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"editorial is not available", response.content)
