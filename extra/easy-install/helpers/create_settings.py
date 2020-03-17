#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A script that creates basic_settings.py file in a given directory
import sys
import os
import getpass
import re
import uuid
from urllib.parse import urlparse

if len(sys.argv) != 2:
    print('Usage: {} config_directory'.format(sys.argv[0]))
    sys.exit(2)

config_directory = sys.argv[1]
basic_settings_file = os.path.join(config_directory, 'basic_settings.py')
open(basic_settings_file, 'a').close()
sys.path.insert(1, config_directory)
import basic_settings  # noqa: E402
regex_default = re.compile(r'^(?!\s*$).+')
regex_num = re.compile(r'^[0-9]*$')


def load_settings(names):
    result = {}
    for name in names:
        try:
            value = getattr(basic_settings, name)
            result[name] = value
        except Exception:
            pass
    return result


def get_input(secure):
    if not secure:
        return input()
    return getpass.getpass()


def parse_question(question, example, original_value):
    result = question
    if original_value is None and example is not None:
        result += ', na przykład ' + str(example)
    else:
        result += ', obecnie [' + str(original_value) + ']'
    return result


def get_value(question, example, requirement, original_value, secure, is_number):
    if not secure:
        print(parse_question(question, example, original_value),
              end=': ')
        reg = regex_num if is_number else regex_default
        text = query_string(original_value is not None, requirement, reg)
        text = repr(text) if text is not None else original_value
    else:
        prompt = question
        if original_value is not None:
            prompt += ', już zostało zapisane, wciśnij ENTER aby pominąć'
        prompt += ': '
        text = repr(getpass.getpass(prompt=prompt))
        if len(text) == 2 and original_value is not None:
            text = original_value
    return text


def query_string(has_original, requirement, regex):
    txt = input()
    if has_original and len(txt) == 0:
        return None
    while len(txt) == 0 or not re.match(regex, txt):
        print('\t' + requirement, end=': ')
        txt = input()
    return txt


def query_yes_no(question, default):
    valid = {'tak': True, 't': True, 'ta': True,
             'nie': False, 'n': False, 'ni': False}
    prompt = ' [T/N] '

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice == '':
            return default
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write('\tDozwolone odpowiedzi to \'tak\' albo \'nie\'\n')


def evaluate_setting(name, question, example, requirement, settings_dict, new_settings_dict, secure=False,
                     is_number=False):
    original_value = settings_dict.get(name, None)
    value = get_value(question, example, requirement, original_value, secure,
                      is_number)
    new_settings_dict[name] = value


simple_names = [
    'SITE_NAME',
    'PUBLIC_ROOT_URL',
    'ALLOWED_HOSTS',
    'SECRET_KEY',
    'EMAIL_HOST',
    'EMAIL_PORT',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'DEFAULT_FROM_EMAIL',
    'SERVER_EMAIL',
    'SEND_USER_ACTIVATION_EMAIL'
]

tuple_of_tuples_names = [
    'ADMINS'
]

tuple_of_tuples_aliases = {
    tuple_of_tuples_names[0]: ('ADMIN_NAME', 'ADMIN_EMAIL'),
}

names = simple_names + [n for t in tuple_of_tuples_aliases.values() for n in t]

settings_names = []
settings_names.extend(simple_names)
settings_names.extend(tuple_of_tuples_names)
settings = load_settings(settings_names)
new_settings = {}

for t in tuple_of_tuples_names:
    first = tuple_of_tuples_aliases[t][0]
    second = tuple_of_tuples_aliases[t][1]
    try:
        settings[first] = settings[t][0][0]
        settings[second] = settings[t][0][1]
    except Exception:
        pass

for n in names:
    if n in settings:
        settings[n] = repr(settings[n])

print('Witaj w kreatorze ustawień sio2.\nWpisz wymaganą wartość, bądź, w '
      'przypadku gdy ta już istnieje,\npo prostu wciśnij '
      'klawisz ENTER, aby ją pozostawić.')

evaluate_setting('SITE_NAME', 'Nazwa strony', 'OIOIOI', '', settings, new_settings)
evaluate_setting('PUBLIC_ROOT_URL', 'Nazwa domeny', 'https://example.com', '',
                 settings, new_settings)
if '//' not in new_settings['PUBLIC_ROOT_URL']:
    new_settings['PUBLIC_ROOT_URL'] = "'http://" + new_settings['PUBLIC_ROOT_URL'][1:]
if not new_settings['PUBLIC_ROOT_URL'].endswith("/'"):
    new_settings['PUBLIC_ROOT_URL'] = new_settings['PUBLIC_ROOT_URL'][:-1] + "/'"

new_settings['ALLOWED_HOSTS'] = "['" + urlparse(new_settings['PUBLIC_ROOT_URL'][1:-1]).hostname + "']"
new_settings['SECRET_KEY'] = settings.get('SECRET_KEY') or "'" + str(uuid.uuid4()) + "'"

evaluate_setting('ADMIN_NAME', 'Imię i nazwisko administratora', 'Jan Kowalski',
                 '', settings, new_settings)
evaluate_setting('ADMIN_EMAIL', 'Adres e-mail administratora',
                 'jan.kowalski@example.com', '', settings, new_settings)

if query_yes_no('Czy chcesz skonfigurować serwer pocztowy? (zalecane)', settings.get('SEND_USER_ACTIVATION_EMAIL') == 'True'):
    evaluate_setting('EMAIL_HOST', 'Adres serwera smtp', 'smtp.example.com', '',
                     settings, new_settings)
    evaluate_setting('EMAIL_PORT', 'Port serwera smtp', '587', 'Tylko cyfry',
                     settings, new_settings, is_number=True)
    evaluate_setting('EMAIL_HOST_USER', 'Nazwa użytkownika (do serwera SMTP)',
                     'user@example.com', '', settings, new_settings)
    evaluate_setting('EMAIL_HOST_PASSWORD', 'Hasło (do serwera SMTP)', None, '', settings, new_settings,
                     secure=True)
    evaluate_setting('DEFAULT_FROM_EMAIL', 'Adres e-mail nadawcy',
                     'user@example.com', '', settings, new_settings)
    new_settings['SERVER_EMAIL'] = 'DEFAULT_FROM_EMAIL'
    new_settings['SEND_USER_ACTIVATION_EMAIL'] = 'True'


original_basic_settings_file = basic_settings_file + '.orig'
os.rename(basic_settings_file, original_basic_settings_file)

print_file = open(basic_settings_file, 'w+')
for name in simple_names:
    value = new_settings.get(name, None)
    if value is not None:
        print_file.write(name + ' = ' + str(value) + '\n')

for t in tuple_of_tuples_names:
    first = new_settings.get(tuple_of_tuples_aliases[t][0])
    second = new_settings.get(tuple_of_tuples_aliases[t][1])
    if first is not None and second is not None:
        print_file.write(t + ' = (\n\t(' + first + ',' + second + '),\n)\n')

print_file.close()
os.remove(original_basic_settings_file)
