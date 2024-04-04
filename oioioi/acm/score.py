from functools import total_ordering

from django.utils.translation import gettext as _

from oioioi.contests.scores import ScoreValue


def format_time(seconds):
    minutes = seconds // 60
    return '%d:%02d' % (minutes // 60, minutes % 60)


@total_ordering
class BinaryScore(ScoreValue):
    """Score representing binary grading: accepted or rejected.

    Sum of binary scores is accepted only when every single score were
    accepted.
    """

    symbol = 'bool'
    accepted = False

    def __init__(self, solved=False):
        self.accepted = solved

    def __add__(self, other):
        return BinaryScore(self.accepted and other.accepted)

    def __eq__(self, other):
        if other is None:
            return False
        return self.accepted == other.accepted

    def __lt__(self, other):
        if other is None:
            return False
        return self.accepted < other.accepted

    def __hash__(self):
        return self.accepted

    @classmethod
    def _from_repr(cls, value):
        return BinaryScore(value == 'accepted')

    def _to_repr(self):
        return 'accepted' if self.accepted else 'rejected'

    def __unicode__(self):
        if self.accepted:
            return _("Accepted")
        else:
            return _("Rejected")

    def __str__(self):
        return self.__unicode__()

    def to_int(self):
        return int(self.accepted)


@total_ordering
class ACMScore(ScoreValue):
    """ACM style score consisting of number of solved problems, total time
    needed for solving problems and time penalty for each
    unsuccessful submission.

    NOTE: When adding :class:`ACMScore`s only scores with positive
    :attr:`problems_solved` are considered to avoid adding
    :attr:`time_passed` or :attr:`penalties_count`
    when :attr:`problems_solved` equals zero. That's because ACM ICPC rules
    states that team doesn't obtain any penalty for nonsolved problems.
    """

    DEFAULT_PENALTY_TIME = 20 * 60  # in seconds

    symbol = 'ACM'
    problems_solved = 0
    time_passed = 0  # in seconds
    penalties_count = 0
    penalty_time = DEFAULT_PENALTY_TIME  # in seconds

    def __init__(self, problems_solved=0, time_passed=0, penalties_count=0,
                       penalty_time=DEFAULT_PENALTY_TIME):
        self.problems_solved = int(problems_solved)
        self.time_passed = int(time_passed)
        self.penalties_count = int(penalties_count)
        self.penalty_time = penalty_time

    def __add__(self, other):
        sum = ACMScore()
        # assume penalty time is the same for both
        sum.penalty_time = self.penalty_time

        if self.problems_solved > 0:
            sum.problems_solved += self.problems_solved
            sum.time_passed += self.time_passed
            sum.penalties_count += self.penalties_count
        if other.problems_solved > 0:
            sum.problems_solved += other.problems_solved
            sum.time_passed += other.time_passed
            sum.penalties_count += other.penalties_count

        return sum

    def __eq__(self, other):
        if other is None:
            return False
        return (self.problems_solved, -self.total_time) == (
            other.problems_solved,
            -other.total_time,
        )

    def __lt__(self, other):
        if other is None:
            return False
        return (self.problems_solved, -self.total_time) < (
            other.problems_solved,
            -other.total_time,
        )

    def __hash__(self):
        return self.total_time

    def __unicode__(self):
        penalty_string = self.penalty_repr()
        time_string = ''
        if self.problems_solved > 0:
            time_string = self.time_passed_repr()
            if penalty_string != '':
                time_string += ' '
        return str(time_string + penalty_string)

    def __str__(self):
        return self.__unicode__()

    def csv_repr(self):
        if self.problems_solved == 0:
            return ''
        return str(self.penalties_count)

    def penalty_repr(self):
        if self.penalties_count <= 3:
            return '*' * self.penalties_count
        else:
            return '*(%d)' % (self.penalties_count,)

    def total_time_repr(self):
        return '%d:%02d:%02d' % (
            self.total_time / 3600,
            (self.total_time % 3600) / 60,
            self.total_time % 60,
        )

    def time_passed_repr(self):
        return format_time(self.time_passed)

    @classmethod
    def _from_repr(cls, value):
        tokens = [int(x) for x in value.split(':')]

        penalty_time = cls.DEFAULT_PENALTY_TIME
        if len(tokens) == 5:
            penalty_time = tokens[4]
            tokens = tokens[:4]

        try:
            _ordering, problems_solved, time_passed, penalties_count = tokens
        except ValueError:
            # try decoding older format
            problems_solved, time_passed, penalties_count = tokens
        return ACMScore(problems_solved, time_passed, penalties_count, penalty_time)

    def _to_repr(self):
        """Store score as string \
           ``"ACM:problems_solved:total_time:penalties_count"`` where:

           ``problems_solved`` is number of problems solved,

           ``total_time`` is total number of seconds needed to solve problems,

           ``penalties_count`` is number of unsuccessful submissions.
        """
        ordering = 10 ** 10 * (self.problems_solved + 1) - self.total_time
        return '%020d:%010d:%010d:%010d:%010d' % (
            ordering,
            self.problems_solved,
            self.time_passed,
            self.penalties_count,
            self.penalty_time,
        )

    @property
    def total_time(self):
        if self.problems_solved > 0:
            return self.time_passed + self.penalties_count * self.penalty_time
        else:
            return 0

    def to_int(self):
        return self.problems_solved
