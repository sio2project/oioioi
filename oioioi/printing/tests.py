from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from oioioi.printing.pdf import generator
from oioioi.contests.models import Contest
import slate
from StringIO import StringIO

SAMPLE_TEXT = """Lorem ipsum dolor sit amet, consectetur adipiscing
        elit. Aenean aliquet commodo vulputate. Fusce vehicula tincidunt
        velit eu dictum. Nulla ultrices sagittis enim, ac dictum felis
        viverra vitae. Sed egestas dui tellus, vel auctor mauris.
        Aliquam erat volutpat. Sed venenatis dapibus ligula, sed gravida est
        varius eu. Aliquam imperdiet ultricies venenatis. Maecenas sed
        sagittis dolor. Praesent tempor mattis orci, ut aliquet justo
        imperdiet sit amet. Aenean porta dui at orci vestibulum aliquet.
        In hac habitasse platea dictumst. Praesent interdum, ipsum ac
        sagittis facilisis, tortor tortor viverra tortor, vehicula
        pellentesque nulla sem nec leo.""" * 100

class TestPDFGenerator(TestCase):
    def test_pdf_generation(self):
        pdf = StringIO(generator(source=SAMPLE_TEXT, header='header'))
        text = slate.PDF(pdf)
        self.assertEqual(9, len(text))
        self.assertIn('Lorem ipsum dolor', text[0])
        self.assertIn('Sed egestas dui tellus', text[4])

class TestPrintingView(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def setUp(self):
        self.client.login(username='test_user')
        self.contest = Contest.objects.get()
        self.url = reverse('print_view',
                           kwargs={'contest_id': self.contest.id})

    def print_file(self, content):
        file = ContentFile(content, name='sample_code.cpp')
        post_data = {
            'file': file
        }
        return self.client.post(self.url, post_data)

    @override_settings(PRINTING_COMMAND=['grep', '%PDF-'])
    def test_print(self):
        response = self.print_file(SAMPLE_TEXT)
        self.assertIn('File has been printed.', response.content)
        # The assert above should fail if there is no "%PDF-" in generated file

    @override_settings(PRINTING_MAX_FILE_SIZE=2048*100)
    def test_page_limit(self):
        response = self.print_file(SAMPLE_TEXT * 2)
        self.assertIn('The page limit exceeded.', response.content)

    def test_file_size_limit(self):
        response = self.print_file(SAMPLE_TEXT * 2)
        self.assertIn('The file size limit exceeded.', response.content)
