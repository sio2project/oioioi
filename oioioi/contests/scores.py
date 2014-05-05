# pylint: disable=E1003
# Bad first argument %s given to super()
"""Each score class is represented in database as single string formatted as
   ``"class_symbol:score_data"`` where ``class_symbol`` is used for binding
   purposes (see :class:`ScoreValue`) and ``score_data`` is score in
   human readable form.

   To create new score class ``MyScore`` you have to choose ``class_symbol``
   and decide how to encode score as ``score_data``.
   MyScore should extend :class:`ScoreValue` and implement its
   unimplemented functions such as :py:func:`__add__`, :py:func:`__cmp__` etc.

   NOTE: when you create a new type of score, make sure that it gets
   registered (its class gets loaded) before any attempt to deserialize its
   instance.
   If you are not sure if this is the case, adding the line
   ``from oioioi.yourapp.score import YourScore`` to ``yourapp.models.py``
   should fix the problem.

   For simple example of score class implementation see :class:`IntegerScore`.
"""

from oioioi.base.utils import ClassInitBase
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


class ScoreValue(ClassInitBase):
    """Base class of all classes that represent a score. Subclass
       :class:`ScoreValue` to implement a custom score."""

    #: A unique, short class identifier prepended to the database
    #: representation of the value. This must be overridden in all subclasses.
    symbol = '__override_in_subclasses__'

    _subclasses = dict()

    @classmethod
    def __classinit__(cls):
        """Adds subclasses' bindings."""

        this_class = globals().get('ScoreValue', cls)
        super(this_class, cls).__classinit__()

        if this_class == cls:
            return

        if cls.symbol == this_class.symbol:
            raise AssertionError('Symbol attribute not defined in %r' % (cls,))
        if cls.symbol in this_class._subclasses:
            raise AssertionError('Duplicate symbol \'%s\' used in both '
                    '%r and %r' % (cls.symbol,
                        this_class._subclasses[cls.symbol], cls))
        this_class._subclasses[cls.symbol] = cls

    def serialize(self):
        """Converts the instance of any subclass to string."""
        return '%s:%s' % (self.symbol, self._to_repr())

    def __repr__(self):
        return self.serialize()

    @staticmethod
    def deserialize(serialized):
        """Invert the operation of :meth:`serialize`."""
        if not serialized:
            return None
        parts = serialized.split(':', 1)
        if len(parts) < 2:
            raise ValidationError(_("Score must look like this: "
                "'<type>:<value>', for example 'int:100', not '%s'."
                % (serialized,)))
        symbol, value = parts
        if symbol in ScoreValue._subclasses:
            return ScoreValue._subclasses[symbol]._from_repr(value)
        else:
            raise ValidationError(_("Unrecognized score type '%s'")
                    % (symbol,))

    def __add__(self, other):
        """Implementation of operator ``+``.

           Used for example when creating user result for round based on scores
           from all problems of the round.

           Must be overridden in all subclasses.
        """
        raise NotImplementedError

    def __cmp__(self, other):
        """Implementation of order. Used to produce ranking, being greater
           means better result.

           Must be overridden in all subclasses.
        """
        raise NotImplementedError

    def __unicode__(self):
        """Returns string representing score, suitable to display to the user.

           Must be overridden in all subclasses.
        """
        raise NotImplementedError

    def _to_repr(self):
        """Returns score data serialized to string, without the class's
           symbol.

           Must be overridden in all subclasses.

           Lexicographical order of serialized data has to correspond to
           the given by :meth:`__cmp__`, it will be used for sorting at db
           level.
        """
        raise NotImplementedError

    @classmethod
    def _from_repr(cls, encoded_value):
        """Creates an instance based on data from :meth:`_to_repr`.

           Must be overridden in all subclasses.
        """
        raise NotImplementedError


class IntegerScore(ScoreValue):
    """Score consisting of integer number.

       Database format: ``"int:<value>"``

       Value is padded with zeros to 19 characters.
    """

    symbol = 'int'

    def __init__(self, value=0):
        assert isinstance(value, (int, long))
        self.value = value

    def __add__(self, other):
        return IntegerScore(self.value + other.value)

    def __cmp__(self, other):
        if not isinstance(other, IntegerScore):
            return cmp(self.value, other)
        return cmp(self.value, other.value)

    def __unicode__(self):
        return unicode(self.value)

    def __repr__(self):
        return "IntegerScore(%s)" % (self.value,)

    @classmethod
    def _from_repr(cls, value):
        return cls(int(value))

    def _to_repr(self):
        return '%019d' % self.value
