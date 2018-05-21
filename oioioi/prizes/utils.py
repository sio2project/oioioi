import random
from operator import itemgetter  # pylint: disable=E0611

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from six.moves import zip

from oioioi.prizes.models import AssignmentNotFound, PrizeForUser
from oioioi.prizes.reports import generate_failure_report


class FairAssignmentNotFound(AssignmentNotFound):
    def __init__(self, prize_giving, matching, conflict_line_nr):
        super(FairAssignmentNotFound, self).__init__(prize_giving)
        self.report = generate_failure_report(matching, conflict_line_nr)

    def send_email(self):
        self.email_msg = EmailMessage(
            body=render_to_string('prizes/nofair_body.txt'),
            attachments=[(_("prizes_conflict.csv"), self.report, 'text/csv')])

        super(FairAssignmentNotFound, self).send_email()


def assign_from_order(prize_giving, order):
    """Take an iterable of (place, user) pairs as order (places may repeat) and
       assign prizes to users.

       In case a fair assignment can't be found (happens only with draws)
       FairAssignmentNotFound is raised.
    """
    order = sorted(list(order), key=itemgetter(0))
    places, users = list(zip(*order)) if order else ([], [])

    # Construct a list of avaiable prizes
    # Note that Prize instances are intended to repeat
    prizes = []
    for p in prize_giving.prize_set.all():
        prizes += [p] * min(p.quantity, len(users) - len(prizes))

    padding = len(users) - len(prizes)
    prizes += [None] * padding

    match = list(zip(places, users, prizes))

    for nr, (current, next_) in enumerate(zip(match, match[1:])):
        if current[2] is None:
            break
        if current[0] == next_[0] and \
                (next_[2] is None or current[2].order < next_[2].order):
            raise FairAssignmentNotFound(prize_giving, match, nr)

    result = [PrizeForUser(user=x[1], prize=x[2])
              for x in match[:len(prizes) - padding]]
    PrizeForUser.objects.bulk_create(result)


def assign_randomly(prize_giving, users):
    x = list(users)
    random.shuffle(x)
    assign_from_order(prize_giving, enumerate(x))
