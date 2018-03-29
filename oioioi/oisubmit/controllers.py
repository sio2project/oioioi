from django.template.context import RequestContext
from django.template.loader import render_to_string

from oioioi.contests.utils import is_contest_admin
from oioioi.programs.controllers import ProgrammingContestController


class OiSubmitContestControllerMixin(object):
    """ContestController mixin that adds extra information about submission
       from the oisubmit app to the submission footer.
    """

    def render_submission_footer(self, request, submission):
        super_footer = super(OiSubmitContestControllerMixin, self). \
                render_submission_footer(request, submission)

        if not hasattr(submission, 'oisubmitextradata') or \
               submission.oisubmitextradata is None or \
               not is_contest_admin(request):
            return super_footer

        def _get_extra(s):
            return getattr(submission.oisubmitextradata, s, '')

        return render_to_string('oisubmit/submission-footer.html',
            context_instance=RequestContext(request, {
                'received_suspected': _get_extra('received_suspected'),
                'comments': _get_extra('comments'),
                'localtime': _get_extra('localtime'),
                'siotime': _get_extra('siotime'),
                'servertime': _get_extra('servertime'),
            })) + super_footer

ProgrammingContestController.mix_in(OiSubmitContestControllerMixin)
