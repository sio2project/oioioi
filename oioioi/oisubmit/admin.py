from django.utils.timezone import localtime
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.admin import SubmissionAdmin
from oioioi.oisubmit.models import OISubmitExtraData
from oioioi.oisubmit.err_dict import INCORRECT_FORM_COMMENTS, SUSPICION_REASONS

class OISubmitSubmissionAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(OISubmitSubmissionAdminMixin, self).__init__(*args, **kwargs)
        self.list_display = self.list_display + ['received_suspected']
        self.list_filter = self.list_filter + \
                ['oisubmitextradata__received_suspected']

    def received_suspected(self, instance):
        received_suspected = getattr(instance.oisubmitextradata,
                'received_suspected', None)
        is_oisubmit = (received_suspected is not None)
        comments = getattr(instance.oisubmitextradata,'comments', '')
        comments = [SUSPICION_REASONS[c] for c in comments.split(',') if c]
        comments = '<br />'.join(map(unicode, comments))
        return render_to_string('received_suspected.html',
                {'received_suspected': received_suspected,
                'is_oisubmit': is_oisubmit, 'comments': comments})
    received_suspected.allow_tags = True
    received_suspected.short_description = _("Received suspected")

    def get_list_select_related(self):
        return super(OISubmitSubmissionAdminMixin, self) \
                .get_list_select_related() + ['oisubmitextradata']

SubmissionAdmin.mix_in(OISubmitSubmissionAdminMixin)
