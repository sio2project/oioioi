from django.test import TestCase
from oioioi.printing.pdf import generator
import slate
from StringIO import StringIO

class TestPrinting(TestCase):
    def test_pdf_generation(self):
        sample_text = """Lorem ipsum dolor sit amet, consectetur adipiscing
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

        pdf = StringIO(generator(source=sample_text, header='header'))
        text = slate.PDF(pdf)
        self.assertEqual(9, len(text))
        self.assertIn('Lorem ipsum dolor', text[0])
        self.assertIn('Sed egestas dui tellus', text[4])
