from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.scores import ScoreValue


class ScoreField(models.CharField):
    """Model field for storing :class:`~oioioi.contests.scores.ScoreValue`s
    """

    description = _("Score")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        super(ScoreField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value is None:
            return None

        # The field might have been filled in code with some strange data
        # we deserialize it to make sure it's in proper format
        if isinstance(value, basestring):
            value = ScoreValue.deserialize(value)

        if isinstance(value, ScoreValue):
            return value.serialize()
        else:
            raise ValidationError('Invalid score value object type')

    def from_db_value(self, value, expression, connection, context):
        if value is None or value == '':
            return None

        return ScoreValue.deserialize(value)

    def value_to_string(self, obj):
        return self.get_prep_value(self._get_val_from_obj(obj))

    def to_python(self, value):
        if isinstance(value, ScoreValue):
            return value

        if value is None or value == '':
            return None

        return ScoreValue.deserialize(value)
