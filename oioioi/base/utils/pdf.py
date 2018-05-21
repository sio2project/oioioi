# pylint: disable=dangerous-default-value
import codecs
import os.path
import shutil
import tempfile

from django.core.files.base import File
from six.moves import range

from oioioi.base.utils.execute import execute
from oioioi.filetracker.utils import stream_file


def generate_pdf(tex_code, filename, extra_args=[], num_passes=3):
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
        pdf_file = open(os.path.splitext(tex_path)[0] + '.pdf')
        return stream_file(File(pdf_file), filename)
    finally:
        shutil.rmtree(tmp_folder)
