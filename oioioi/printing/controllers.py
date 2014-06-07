from oioioi.contests.controllers import ContestController


class PrintingContestControllerMixin(object):
    """Disallow printing by default."""
    def can_print_files(self, request):
        return False

ContestController.mix_in(PrintingContestControllerMixin)
