from functools import total_ordering

from oioioi.contests.scores import ScoreValue


@total_ordering
class FloatScore(ScoreValue):
    symbol = 'float'

    def __init__(self, value):
        assert isinstance(value, float) or isinstance(value, int)
        self.value = float(value)

    def __add__(self, other):
        if not isinstance(other, FloatScore):
            return FloatScore(self.value + other)
        return FloatScore(self.value + other.value)

    def __mul__(self, other):
        if not isinstance(other, FloatScore):
            return FloatScore(self.value * other)
        return FloatScore(self.value * other.value)

    __rmul__ = __mul__

    def __eq__(self, other):
        if not isinstance(other, FloatScore):
            return self.value == other
        return self.value == other.value

    def __lt__(self, other):
        if not isinstance(other, FloatScore):
            return self.value < other
        return self.value < other.value

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return str(self.value)

    def __repr__(self):
        return "FloatScore(%s)" % (self.value,)

    @classmethod
    def _from_repr(cls, value):
        return cls(float(value))

    def _to_repr(self):
        return '%017.2f' % self.value

    def to_int(self):
        return int(self.value)
