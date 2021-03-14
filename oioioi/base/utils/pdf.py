import codecs
import io
import os.path
import shutil
import tempfile

import pdfminer.layout
import six
from django.core.files.base import File
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from six.moves import range

from oioioi.base.utils.execute import execute
from oioioi.filetracker.utils import stream_file


def generate_pdf(tex_code, filename, extra_args=None, num_passes=3):
    if extra_args is None:
        extra_args = []

    # Create temporary file and folder
    tmp_folder = tempfile.mkdtemp()
    try:
        tex_filename = 'doc.tex'
        tex_path = os.path.join(tmp_folder, tex_filename)

        with codecs.open(tex_path, 'w', 'utf-8') as f:
            f.write(tex_code)

        command = ['pdflatex']
        command.extend(extra_args)
        command.append(tex_filename)
        for _i in range(num_passes):
            execute(command, cwd=tmp_folder)

        # Get PDF file contents
        pdf_file = io.open(os.path.splitext(tex_path)[0] + '.pdf', "rb")
        return stream_file(File(pdf_file), filename)
    finally:
        shutil.rmtree(tmp_folder)


def extract_text_from_pdf(pdf_file):
    # pdf_file must be a a file-like object
    # returns a list of strings, each string containing text from one page

    # the char_margin is needed because pdfminer.six has a problem
    # that causes lines with big spacing between text blocks to be split into
    # many lines, sometimes out-of-reasonable-orded
    # the value needs to be high enough so that char_width * char_margin > page_width

    laparams = pdfminer.layout.LAParams(char_margin=2000)

    pages = []
    output_string = six.BytesIO()
    rsrcmgr = PDFResourceManager()
    device = TextConverter(rsrcmgr, output_string, codec='latin-1', laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for page in PDFPage.get_pages(
        pdf_file,
        None,
        maxpages=0,
        password='',
        caching=False,
        check_extractable=True,
    ):
        interpreter.process_page(page)
        pages.append(output_string.getvalue())

    output_string.close()
    return pages
