from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from oioioi.programs.controllers import ProgrammingContestController


class SubmitServiceMixinForProgrammingContestController(object):
    def adjust_submission_form(self, request, form):
        super(SubmitServiceMixinForProgrammingContestController, self) \
            .adjust_submission_form(request, form)
        form.fields['file'].help_text = \
            mark_safe(form.fields['file'].help_text + _(
                " Alternatively, you can "
                "<a href='%s'>submit your solutions from terminal</a>."
            ) % reverse('submitservice_view_user_token',
                        kwargs={'contest_id': request.contest.id}))

ProgrammingContestController.mix_in(
    SubmitServiceMixinForProgrammingContestController)
