from functools import total_ordering

from oioioi.contests.scores import IntegerScore, ScoreValue


@total_ordering
class ScoreDistribution:
    def __init__(self, scores=None):
        if scores:
            assert isinstance(scores, list)
            assert len(scores) == 10
            self.scores = scores
        else:
            self.scores = [0] * 10

    def __add__(self, other):
        return ScoreDistribution([a + b for (a, b) in zip(self.scores, other.scores, strict=False)])

    def __eq__(self, other):
        return self.scores == other.scores

    def __lt__(self, other):
        return self.scores < other.scores

    def update(self, score):
        assert score >= 0 and score <= 10
        if score > 0:
            self.scores[10 - score] += 1

    def __repr__(self):
        return "ScoreDistribution(%s)" % ", ".join(["%d: %d" % p for p in zip(reversed(list(range(1, 11))), self.scores, strict=False)])

    def _to_repr(self):
        return ":".join(["%05d" % p for p in self.scores])

    @classmethod
    def _from_repr(cls, value):
        return cls([int(p) for p in value.split(":")])


@total_ordering
class PAScore(ScoreValue):
    """PA style score.

    It consists of a number of points scored, together with their
    distribution.
    When two users get the same number of points, then the number of tasks
    for which they got 10pts (maximal score) is taken into consideration.
    If this still does not break the tie, number of 9 point scores is
    considered, then 8 point scores etc.
    """

    symbol = "PA"

    def __init__(self, points=None, distribution=None):
        if points:
            assert isinstance(points, IntegerScore)
            self.points = points
        else:
            self.points = IntegerScore(0)
        if distribution:
            assert isinstance(distribution, ScoreDistribution)
            self.distribution = distribution
        else:
            self.distribution = ScoreDistribution()
            self.distribution.update(self.points.value)

    def __add__(self, other):
        return PAScore(self.points + other.points, self.distribution + other.distribution)

    def __eq__(self, other):
        if not isinstance(other, PAScore):
            return self.points == other
        return (self.points, self.distribution) == (other.points, other.distribution)

    def __lt__(self, other):
        if not isinstance(other, PAScore):
            return self.points < other
        return (self.points, self.distribution) < (other.points, other.distribution)

    def __unicode__(self):
        return str(self.points)

    def __repr__(self):
        return "PAScore(%r, %r)" % (self.points, self.distribution)

    def __str__(self):
        return str(self.points)

    @classmethod
    def _from_repr(cls, value):
        points, distribution = value.split(";")
        return cls(
            points=IntegerScore._from_repr(points),
            distribution=ScoreDistribution._from_repr(distribution),
        )

    def _to_repr(self):
        return "%s;%s" % (self.points._to_repr(), self.distribution._to_repr())

    def to_int(self):
        return self.points.to_int()
