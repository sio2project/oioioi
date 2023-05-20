from django.core.files.base import ContentFile
from django.test.utils import override_settings
from django.urls import reverse
from io import BytesIO
import pytest
import mimetypes

from oioioi.base.tests import TestCase
from oioioi.base.utils.pdf import extract_text_from_pdf
from oioioi.contests.controllers import ContestController
from oioioi.contests.models import Contest
from oioioi.printing.pdf import generator

SAMPLE_TEXT = (
    """Lorem ipsum dolor sit amet, consectetur adipiscing
        elit. Aenean aliquet commodo vulputate. Fusce vehicula tincidunt
        velit eu dictum. Nulla ultrices sagittis enim, ac dictum felis
        viverra vitae. Sed egestas dui tellus, vel auctor mauris.
        Aliquam erat volutpat. Sed venenatis dapibus ligula, sed gravida est
        varius eu. Aliquam imperdiet ultricies venenatis. Maecenas sed
        sagittis dolor. Praesent tempor mattis orci, ut aliquet justo
        imperdiet sit amet. Aenean porta dui at orci vestibulum aliquet.
        In hac habitasse platea dictumst. Praesent interdum, ipsum ac
        sagittis facilisis, tortor tortor viverra tortor, vehicula
        pellentesque nulla sem nec leo."""
    * 100
)


class PrintingTestContestController(ContestController):
    def can_print_files(self, request):
        return True


class TestPDFGenerator(TestCase):
    def test_pdf_generation(self):
        pdf = BytesIO(generator(source=SAMPLE_TEXT, header='header'))
        text = extract_text_from_pdf(pdf)
        self.assertEqual(9, len(text))
        self.assertIn(b'Lorem ipsum dolor', text[0])
        self.assertIn(b'Sed egestas dui tellus', text[4])


mimetypes.init()
mimetypes_db_needed = pytest.mark.xfail(
    '.cpp' not in mimetypes.types_map, reason="The mimetypes db is incomplete"
)


class TestPrintingView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.contest = Contest.objects.get()
        self.contest.controller_name = (
            'oioioi.printing.tests.PrintingTestContestController'
        )
        self.contest.save()
        self.url = reverse('print_view', kwargs={'contest_id': self.contest.id})

    def print_file(self, content):
        file = ContentFile(content.encode('utf-8'), name='sample_code.cpp')
        post_data = {'file': file}
        return self.client.post(self.url, post_data)

    @mimetypes_db_needed
    @override_settings(PRINTING_COMMAND=['grep', '%PDF-'])
    def test_print(self):
        response = self.print_file(SAMPLE_TEXT)
        self.assertContains(response, 'File has been printed.')
        # The assert above should fail if there is no "%PDF-" in generated file

    @mimetypes_db_needed
    @override_settings(PRINTING_MAX_FILE_SIZE=2048 * 100)
    def test_page_limit(self):
        response = self.print_file(SAMPLE_TEXT * 2)
        self.assertContains(response, 'The page limit exceeded.')

    def test_file_size_limit(self):
        response = self.print_file(SAMPLE_TEXT * 2)
        self.assertContains(response, 'The file size limit exceeded.')
