from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from fpdf import FPDF

import os

FONT_DIR = os.path.join(os.path.dirname(__file__), 'font')
FONT = getattr(settings, 'PRINTING_FONT',
    os.path.join(FONT_DIR, 'DejaVuSerifCondensed.ttf'))
FONT_SIZE = getattr(settings, 'PRINTING_FONT_SIZE', 8)
MM_IN_POINT = 0.35


class PageLimitExceeded(Exception):
    pass


class PrintPDF(FPDF):
    """FPDF object with two column layout, header and footer"""
    def __init__(self, *args, **kwargs):
        self.header_text = kwargs.pop('header', u'')
        super(PrintPDF, self).__init__(*args, **kwargs)
        self.alias_nb_pages()
        self.initial_l_margin = self.l_margin
        self.background_gray = 200  # The gray level. Value between 0 and 255
        self.column_width = (self.w - self.l_margin - self.r_margin) / 2
        self.center = self.l_margin + self.column_width
        self.cell_height = FONT_SIZE * MM_IN_POINT
        self.col = 0
        self.set_col(0)

    def set_col(self, col):
        self.col = col
        if col < 1:
            margin = self.initial_l_margin
        else:
            margin = self.center
        self.set_left_margin(margin)
        self.set_x(margin)

    def accept_page_break(self):
        if self.page_no() == settings.PRINTING_MAX_FILE_PAGES:
            raise PageLimitExceeded

        if self.col < 1:
            self.set_col(self.col + 1)
            self.set_y(16)
            return False
        else:
            self.set_col(0)
            return True

    def gray_cell(self, *args, **kwargs):
        self.set_fill_color(self.background_gray)
        kwargs['fill'] = True
        self.cell(*args, **kwargs)
        self.set_fill_color(0)

    def header(self):
        self.set_font('USER_FONT', size=FONT_SIZE)

        self.gray_cell(w=0, h=self.cell_height,
                       txt=self.header_text, border=1, ln=1, align='C')

    def footer(self):
        self.set_left_margin(self.initial_l_margin)
        self.set_y(self.h - self.b_margin)

        self.set_font('Times', size=FONT_SIZE)
        # FPDF does not support {nb} alias with unicode.
        #  It's already fixed in hg repository, we are waiting for release.
        self.gray_cell(
            w=0, h=self.cell_height, txt=_("Page %s/{nb}") % self.page_no(),
            border=1, ln=1, align='C')

        # Draw lines on margins and between columns
        self.line(self.initial_l_margin, self.t_margin, self.initial_l_margin,
                  self.h - self.b_margin)
        self.line(self.center, self.t_margin + self.cell_height, self.center,
                  self.h - self.b_margin)
        self.line(
            self.w - self.r_margin, self.t_margin, self.w - self.r_margin,
            self.h - self.b_margin)


def generator(source, header):
    pdf = PrintPDF(orientation='L', header=header)
    pdf.add_font('USER_FONT', '', FONT, uni=True)

    pdf.add_page()
    pdf.set_font('USER_FONT', size=FONT_SIZE)
    pdf.multi_cell(
        w=pdf.column_width, h=pdf.cell_height, txt=source, border=0, align='L')
    return pdf.output(dest='S')
