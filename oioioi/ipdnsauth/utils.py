import re


def username_to_hostname(username):
    hostname = re.sub(r'[^a-z0-9]', '', username.lower())
    if not hostname:
        hostname = 'samepodkreslniki'
    return hostname
