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

    symbol = 'ACM'
    problems_solved = 0
    time_passed = 0 # in seconds
    penalties_count = 0
    penalty_time = 20*60 # in seconds


    def __init__(self, problems_solved=0, time_passed=0, penalties_count=0):
        self.problems_solved = int(problems_solved)
        self.time_passed = int(time_passed)
        self.penalties_count = int(penalties_count)

    def __add__(self, other):
        sum = ACMScore()
        if self.problems_solved > 0:
            sum.problems_solved += self.problems_solved
            sum.time_passed += self.time_passed
            sum.penalties_count += self.penalties_count
        if other.problems_solved > 0:
            sum.problems_solved += other.problems_solved
            sum.time_passed += other.time_passed
            sum.penalties_count += other.penalties_count

        return sum

    def __cmp__(self, other):
        return cmp((self.problems_solved, -self.total_time),
            (other.problems_solved, -other.total_time))

    def __hash__(self):
        return self.total_time

    def __str__(self):
        penalty_string = self.penalty_repr()
        time_string = ''
        if self.problems_solved > 0:
            time_string = self.total_time_repr()
            if penalty_string != '':
                time_string += ' '
        return time_string + penalty_string

    def penalty_repr(self):
        if self.penalties_count <= 3:
            return '*' * self.penalties_count
        else:
            return '*(%d)' % (self.penalties_count,)


    def total_time_repr(self):
        return '%d:%02d:%02d' % (self.total_time/3600,
                                (self.total_time % 3600)/60,
                                self.total_time % 60)

    @classmethod
    def _from_repr(cls, value):
        problems_solved, total_time, penalties_count = map(int,
                                                           value.split(':'))
        return ACMScore(problems_solved,
                        total_time - cls.penalty_time * penalties_count,
                        penalties_count)

    def _to_repr(self):
        """Store score as string \
           ``"ACM:problems_solved:total_time:penalties_count"`` where:

           ``problems_solved`` is number of problems solved,

           ``total_time`` is total number of seconds needed to solve problems,

           ``penalties_count`` is number of unsuccessful submissions.
        """
        return '%d:%d:%d' % (self.problems_solved, self.total_time,
                self.penalties_count)

    @property
    def total_time(self):
        if self.problems_solved > 0:
            return self.time_passed + self.penalties_count * self.penalty_time
        else:
            return 0


