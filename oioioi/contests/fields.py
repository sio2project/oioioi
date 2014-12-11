from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.scores import ScoreValue


class ScoreField(models.CharField):
    """Model field for storing :class:`~oioioi.contests.scores.ScoreValue`s
    """

    __metaclass__ = models.SubfieldBase

    description = _("Score")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        super(ScoreField, self).__init__(*args, **kwargs)

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
