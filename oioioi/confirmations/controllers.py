from oioioi.confirmations.utils import send_submission_receipt_confirmation
from oioioi.programs.controllers import ProgrammingContestController


class ConfirmationContestControllerMixin:
    """Adds an option to contest controllers to send participants a proof of
    receiving their submissions.
    """

    def should_confirm_submission_receipt(self, request, submission):
        return False

    def create_submission(self, request, *args, **kwargs):
        submission = super(ConfirmationContestControllerMixin, self).create_submission(request, *args, **kwargs)

        if self.should_confirm_submission_receipt(request, submission):
            send_submission_receipt_confirmation(request, submission)
        return submission


ProgrammingContestController.mix_in(ConfirmationContestControllerMixin)
