import re
from unicodedata import category as u_cat

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _


def validate_whitespaces(value):
    if not value.strip():
        raise ValidationError(_("This field must contain a non-whitespace character."))


db_string_id_re = re.compile(r'^[a-z0-9_-]+$')
#: We are forcing only lowercase letters, as some database collations use
#: case insensitive string comparison.
validate_db_string_id = RegexValidator(
    db_string_id_re,
    _(
        "Enter a valid 'slug' consisting of lowercase letters, numbers, "
        "underscores or hyphens."
    ),
    'invalid',
)


@deconstructible
class UnicodeValidator(object):
    unicode_categories = []
    message = _('Enter a valid value.')
    code = 'invalid'
    allow_spaces = False

    def __init__(
        self, unicode_categories=None, message=None, code=None, allow_spaces=None
    ):
        if unicode_categories is not None:
            self.unicode_categories = unicode_categories
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if allow_spaces is not None:
            self.allow_spaces = allow_spaces

    def __call__(self, value):
        """
        Validates that the input matches the category restrictions of
        unicode_categories. Additionally, if allow_spaces is True,
        then allows spaces, but not at the beginning/end.
        """
        value = force_text(value)
        n = len(value)
        for i, letter in enumerate(value):
            c = u_cat(letter)
            if c not in self.unicode_categories and (
                i == 0 or i == n - 1 or c != 'Zs' or not self.allow_spaces
            ):
                raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return (
            isinstance(other, UnicodeValidator)
            and self.unicode_categories == other.unicode_categories
            and self.message == other.message
            and self.code == other.code
            and self.allow_spaces == other.allow_spaces
        )

    def __ne__(self, other):
        return not (self == other)
