from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from oioioi.base.tests import TestCase
from oioioi.problems.models import Problem, ProblemAttachment


class TestProblemAttachmentValidation(TestCase):
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

    def test_clean_valid_content(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="file-editorial",
            content=ContentFile(b"file content", name="editorial.pdf"),
            is_editorial=True,
        )
        pa.clean()  # Should not raise

    def test_clean_valid_url(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="url-editorial",
            url="https://youtube.com/watch?v=123",
            is_editorial=True,
        )
        pa.clean()  # Should not raise

    def test_clean_invalid_both(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="both-editorial",
            content=ContentFile(b"file content", name="editorial.pdf"),
            url="https://youtube.com/watch?v=123",
            is_editorial=True,
        )
        with self.assertRaises(ValidationError):
            pa.clean()

    def test_clean_invalid_none(self):
        pa = ProblemAttachment(
            problem=self.problem,
            description="none-editorial",
            is_editorial=True,
        )
        with self.assertRaises(ValidationError):
            pa.clean()
