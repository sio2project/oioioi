import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


def validate_whitespaces(value):
        if not value.strip():
            raise ValidationError(
                _("This field must contain a non-whitespace character."))

db_string_id_re = re.compile(r'^[a-z0-9_-]+$')
#: We are forcing only lowercase letters, as some database collations use
#: case insensitive string comparison.
validate_db_string_id = RegexValidator(db_string_id_re,
        _("Enter a valid 'slug' consisting of lowercase letters, numbers, "
          "underscores or hyphens."), 'invalid')
