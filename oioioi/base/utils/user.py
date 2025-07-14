import re

from django.core.exceptions import ValidationError

from oioioi.base.utils.validators import UnicodeValidator

USERNAME_REGEX = r"^[a-zA-Z0-9_]+$"

""" All characters constituting users name and surname must
    belong to one of the categories specified in
    `UNICODE_CATEGORY_LIST`. For a guide of unicode categories
    see: https://unicodebook.readthedocs.io/unicode.html
"""
UNICODE_CATEGORY_LIST = [
    "Ll",
    "Lm",
    "Lo",
    "Lt",
    "Lu",
    "Nd",
    "Pf",
    "Pd",
    "Pi",
    "Pe",
    "Pc",
    "Sc",
]


def check_unicode_text(text, allow_spaces=False):
    try:
        UnicodeValidator(unicode_categories=UNICODE_CATEGORY_LIST, allow_spaces=allow_spaces)(text)
        return True
    except ValidationError:
        return False


def has_valid_username(user):
    return user is None or user.is_anonymous or re.match(USERNAME_REGEX, user.username) is not None


def has_valid_name(user):
    return (
        user is None or user.is_anonymous or (check_unicode_text(user.first_name, allow_spaces=True) and check_unicode_text(user.last_name, allow_spaces=True))
    )
