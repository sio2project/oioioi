import re

USERNAME_REGEX = r'^[a-zA-Z0-9_]+$'


def has_valid_username(user):
    return user is None or user.is_anonymous() or \
            re.match(USERNAME_REGEX, user.username) is not None
