from StringIO import StringIO

import unicodecsv
from django.utils.translation import ugettext as _


def generate_success_report(pg):
    # Avoid circular import.
    from oioioi.prizes.models import PrizeForUser

    pfus = PrizeForUser.objects.select_related('user', 'prize') \
            .filter(prize__prize_giving=pg)

    f = StringIO()
    w = unicodecsv.writer(f, encoding='utf-8')

    w.writerow((_("Prize"), _("User")))
    for pfu in pfus:
        w.writerow((pfu.prize, pfu.user))

    report = f.getvalue()
    f.close()

    return report


def generate_failure_report(matching, conflict_line_nr):
    max_place_awarded = max(
            place for place, user, prize in matching if prize)
    truncated_matching = (
            (place, user, prize if prize else _("Nothing"))
            for place, user, prize in matching
            if place <= max_place_awarded)

    f = StringIO()
    w = unicodecsv.writer(f, encoding='utf-8')

    w.writerow((_("Place"), _("User"), _("Prize")))
    for nr, row in enumerate(truncated_matching):
        if conflict_line_nr in (nr, nr - 1):
            row += ('<<<<<<<<<<<<<',)
        w.writerow(row)

    report = f.getvalue()
    f.close()

    return report
