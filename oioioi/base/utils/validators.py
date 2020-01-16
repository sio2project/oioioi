import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, force_text
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext_lazy as _
from unicodedata import category as u_cat


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


@deconstructible
class UnicodeValidator(object):
    unicode_categories = []
    message = _('Enter a valid value.')
    code = 'invalid'
    inverse_match = False

    def __init__(self, unicode_categories=None, message=None, code=None,
                 inverse_match=None):
        if unicode_categories is not None:
            self.unicode_categories = unicode_categories
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if inverse_match is not None:
            self.inverse_match = inverse_match

    def __call__(self, value):
        """
        Validates that the input matches the category restrictions of
        unicode_categories if inverse_match is False, otherwise
        raises ValidationError.
        """
        text = force_text(value)
        for letter in text:
            if u_cat(letter) in self.unicode_categories == self.inverse_match:
                raise ValidationError(self.message, code=self.code)

    def __eq__(self, other):
        return isinstance(other, UnicodeValidator) and \
            self.unicode_categories == other.unicode_categories and \
            self.message == other.message and \
            self.code == other.code and \
            self.inverse_match == other.inverse_match

    def __ne__(self, other):
        return not (self == other)
