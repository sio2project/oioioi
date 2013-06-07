from django.utils.translation import ugettext_lazy as _

SUSPICION_REASONS = {
    'SLE': _("Submission limit exceeded."),
    'BEFORE_START': _("Sent before the start of the round."),
    'AFTER_END': _("Sent after the end of the round."),
    'TIMES_DIFFER': _("Submissiontime and servertime differs too much."),
}

INCORRECT_FORM_COMMENTS = {
    'problem_shortname': _("Incorrect problem short name."),
    'magickey': _("Script error."),
    'localtime': _("Error sending date."),
    'siotime': _("Error sending date."),
}
