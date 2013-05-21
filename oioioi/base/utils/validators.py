from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def validate_whitespaces(value):
        if not value.strip():
            raise ValidationError(
                _("This field must contain a non-whitespace character."))
