from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from oioioi.programs.controllers import ProgrammingContestController


class SubmitServiceMixinForProgrammingContestController(object):
    """ContestController mixin that adds information about the possibility to
    submit solutions from terminal.
    """

    def adjust_submission_form(self, request, form, problem_instance):
        super(
            SubmitServiceMixinForProgrammingContestController, self
        ).adjust_submission_form(request, form, problem_instance)
        form.fields['file'].help_text = mark_safe(
            form.fields['file'].help_text
            + _(
                " Alternatively, you can "
                "<a href='%s'>submit your solutions from terminal</a>."
            )
            % reverse(
                'submitservice_view_user_token',
                kwargs={'contest_id': request.contest.id},
            )
        )


ProgrammingContestController.mix_in(SubmitServiceMixinForProgrammingContestController)
