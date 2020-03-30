# !/usr/bin/python3
# coding=utf-8
# Script that creates user_settings.py file in a given directory


import sys
import os
import getpass
import importlib
import re

if len(sys.argv) != 2:
    print('Usage: update_settings deployment_directory')
    sys.exit(0)

deployment_folder = sys.argv[1]
user_settings_file = os.path.join(deployment_folder, 'user_settings.py')
open(user_settings_file, 'a').close()
sys.path.insert(1, deployment_folder)
user_settings = importlib.import_module('user_settings')
regex_default = re.compile(r'^(?!\s*$).+')
regex_num = re.compile(r'^[0-9]*$')


def load_settings(names):
    result = {}
    for name in names:
        try:
            value = getattr(user_settings, name)
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


def get_value(question, example, clue, original_value, secure, is_number):
    if not secure:
        print(parse_question(question, example, original_value),
              end=': ')
        reg = regex_num if is_number else regex_default
        text = query_string(original_value is not None, clue, reg)
        text = text if text is not None else original_value
    else:
        prompt = question
        if original_value is not None:
            prompt += ', już zostało zapisane, wciśnij ENTER aby pominąć'
        prompt += ': '
        text = getpass.getpass(prompt=prompt)
        if len(text) == 0 and original_value is not None:
            text = original_value

    if not is_number:
        text = '\'' + text + '\''
    return text


def query_string(has_original, clue, regex):
    txt = input()
    if has_original and len(txt) == 0:
        return None
    while len(txt) == 0 or not re.match(regex, txt):
        print('\t' + clue, end=': ')
        txt = input()
    return txt


def query_yes_no(question):
    valid = {'tak': True, 't': True, 'ta': True,
             'nie': False, 'n': False, 'ni': False}
    default = 'nie'
    prompt = ' [t/N] '

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write('\tDozwolone odpowiedzi to \'tak\' albo \'nie\'\n')


def evaluate_setting(name, question, example, clue, settings_dict, secure=False,
                     is_number=False):
    original_value = settings_dict.get(name, None)
    value = get_value(question, example, clue, original_value, secure,
                      is_number)
    settings_dict[name] = value


string_names = [
    'SITE_NAME',
    'PUBLIC_ROOT_URL',
    'DEFAULT_FROM_EMAIL',
    'EMAIL_HOST',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'EMAIL_SUBJECT_PREFIX',
    'DEFAULT_FROM_ADDRESS',
    'SERVER_EMAIL'
]

integer_names = [
    'EMAIL_PORT'
]

tuple_of_tuples_names = [
    'ADMINS'
]

tuple_of_tuples_aliases = {
    tuple_of_tuples_names[0]: ('ADMIN_NAME', 'ADMIN_EMAIL'),
}

settings_names = []
settings_names.extend(string_names)
settings_names.extend(tuple_of_tuples_names)
settings_names.extend(integer_names)
settings = load_settings(settings_names)
for t in tuple_of_tuples_names:
    first = tuple_of_tuples_aliases.get(t)[0]
    second = tuple_of_tuples_aliases.get(t)[1]
    settings[first] = settings.get(t)[0][0]
    settings[second] = settings.get(t)[0][1]

os.system('clear')
print('Witaj w kreatorze ustawień sio2.\nWpisz wymaganą wartość, bądź w '
      'przypadku gdy istnieje już wartość\nto możesz wcisnąć '
      'klawisz ENTER, aby ją pozostawić')

evaluate_setting('SITE_NAME', 'Nazwa strony', 'OIOIOI', '', settings)
evaluate_setting('PUBLIC_ROOT_URL', 'Nazwa domeny', 'https://my-site.com', '',
                 settings)
evaluate_setting('ADMIN_NAME', 'Imię i nazwisko administratora', 'Jan Kowalski',
                 '',
                 settings)
evaluate_setting('ADMIN_EMAIL', 'Adres e-mail administratora',
                 'admin@gmail.com', '', settings)

if query_yes_no('Czy chcesz skonfigurować serwer pocztowy?'):
    evaluate_setting('EMAIL_HOST', 'Adres hosta smtp', 'smtp.gmail.com', '',
                     settings)
    evaluate_setting('EMAIL_PORT', 'Port serwera smtp', '587', 'Tylko cyfry',
                     settings, is_number=True)
    evaluate_setting('EMAIL_HOST_USER', 'Nazwa użytkownika (adres e-mail)',
                     'my-mail@gmail.com', '', settings)
    evaluate_setting('DEFAULT_FROM_EMAIL', 'Alias adresu e-mail nadawcy',
                     'my-site@my-site.com', '', settings)
    evaluate_setting('EMAIL_HOST_PASSWORD', 'Hasło', None, '', settings,
                     secure=True)

original_user_settings_file = user_settings_file + '.orig'
os.rename(user_settings_file, original_user_settings_file)

print_file = open(user_settings_file, 'w+')
for name in string_names:
    value = settings.get(name, None)
    if value is not None:
        if value[0] != '\'':
            value = '\'' + value + '\''
        print_file.write(name + ' = ' + str(value) + '\n')

for t in tuple_of_tuples_names:
    first = settings.get(tuple_of_tuples_aliases.get(t)[0], None)
    second = settings.get(tuple_of_tuples_aliases.get(t)[1], None)
    if first is not None and second is not None:
        print_file.write(t + ' = (\n\t(' + first + ',' + second + '),\n)\n')

for num in integer_names:
    value = settings.get(num, None)
    if value is not None:
        print_file.write(num + ' = ' + str(value) + '\n')

print_file.close()
os.remove(original_user_settings_file)
