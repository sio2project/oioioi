"""Each score class is represented in database as single string formatted as
   ``"class_symbol:score_data"`` where ``class_symbol`` is used for binding
   purposes (see :class:`ScoreValue`) and ``score_data`` is score in
   human readable form.

   To create new score class ``MyScore`` you have to choose ``class_symbol``
   and decide how to encode score as ``score_data``.
   MyScore should extend :class:`ScoreValue` and implement its
   unimplemented functions such as :py:func:`__add__`, :py:func:`__cmp__` etc.

   For simple example of score class implementation see :class:`IntegerScore`.
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _
from south.modelsinspector import add_introspection_rules
from oioioi.contests.scores import ScoreValue

class ScoreField(models.CharField):
    """Model field for storing :class:`~oioioi.contests.scores.ScoreValue`s
    """

    __metaclass__ = models.SubfieldBase

    description = _("Score")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        models.Field.__init__(self, *args, **kwargs)

    def get_prep_value(self, value):
        if value is None:
            return None
        else:
            return value.serialize()

    def value_to_string(self, obj):
        return self.get_prep_value(self._get_val_from_obj(obj))

    def to_python(self, value):
        if value is None:
            return None
        elif isinstance(value, ScoreValue):
            return value
        elif isinstance(value, basestring):
            if value == '':
                return None
            return ScoreValue.deserialize(value)
        else:
            raise ValueError("ScoreField.to_python got neither ScoreValue nor "
                    "string: %r" % (value,))

add_introspection_rules([], ["^oioioi\.contests\.fields\.ScoreField"])
