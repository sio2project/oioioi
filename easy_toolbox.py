#!/usr/bin/env python3

# pip requirements:
#   python ^3.6
#   inquirer     (only for GUI)
# 
# system:
#   docker
#   docker-compose


# This script was created in order to help the users
# execute commands faster. The main idea was to omit
# copy-pasting commands from GitHub. This script
# is prepared and should be upgraded or/and extended
# for any future needs.

import sys
import os


BASE_DOCKER_COMMAND = "OIOIOI_UID=$(id -u) docker-compose" + \
                      " -f docker-compose-dev.yml" + \
                      " -f extra/docker/docker-compose-dev-noserver.yml"

RAW_COMMANDS = [
    ("build", "Build OIOIOI container from source.", "build", True),
    ("up", "Run all SIO2 containers", "up -d"),
    ("down", "Stop and remove all SIO2 containers", "down", True),
    ("run", "Run server", "{exec} web python3 manage.py runserver 0.0.0.0:8000"),
    ("stop", "Stop all SIO2 containers", "stop"),
    ("bash", "Open command prompt on web container.", "{exec} web bash"),
    ("bash-db", "Open command prompt on database container.", "{exec} db bash"),
    # This one CLEARS the database. Use wisely.
    ("flush-db", "Clear database.", "{exec} web python manage.py flush --noinput", True),
    ("add-superuser", "Create admin_admin.",
     "{exec} web python manage.py loaddata ../oioioi/oioioi_cypress/cypress/fixtures/admin_admin.json"),
    ("test", "Run unit tests.", "{exec} web ../oioioi/test.sh"),
    ("test-slow", "Run unit tests. (--runslow)", "{exec} web ../oioioi/test.sh --runslow"),
    ("test-abc", "Run specific test file. (edit the toolbox)",
     "{exec} web ../oioioi/test.sh -v oioioi/problems/tests/test_task_archive.py"),
    ("test-coverage", "Run coverage tests.",
     "{exec} 'web' ../oioioi/test.sh oioioi/problems --cov-report term --cov-report xml:coverage.xml --cov=oioioi"),
    ("cypress-apply-settings", "Apply settings for CyPress.",
     "{exec} web bash -c \"echo CAPTCHA_TEST_MODE=True >> settings.py\""),
]

longest_command_arg = max([len(command[0]) for command in RAW_COMMANDS])


class Help(Exception):
    pass


class Option:
    def __init__(self, _arg, _help, _command, _warn=False):
        self.arg = _arg
        self.help = _help
        self.command = _command
        self.warn = _warn

    # If we use exec we should add -T for GitHub actions (disable tty).
    def fill_tty(self, disable=False):
        self.command = self.command.format(exec="exec -T" if disable else "exec")

    def long_str(self) -> str:
        return f"Option({self.arg}, Description='{self.help}', Command='{self.command}')"

    def __str__(self) -> str:
        spaces = longest_command_arg - len(self.arg)
        return f"[{self.arg}] {' ' * spaces} {self.help}"


COMMANDS = [Option(*x) for x in RAW_COMMANDS]


def check_commands() -> None:
    if len(set([opt.arg for opt in COMMANDS])) != len(COMMANDS):
        raise Exception("Error in COMMANDS. Same name was declared for more then one command.")


NO_INPUT = False


def get_action_from_args() -> Option:
    # not flags
    arguments = []

    for arg in sys.argv[1:]:
        if arg in ['--help', '-h']:
            raise Help()
        elif arg in ['--no-input', '-i']:
            global NO_INPUT
            NO_INPUT = True
        else:
            arguments.append(arg)

    if len(arguments) < 1:
        return None
    if len(arguments) > 1:
        raise Exception("Too many arguments!")

    candidates = list(filter(lambda opt: opt.arg == arguments[0], COMMANDS))
    if len(candidates) < 1:
        raise Exception("No argument was found!")
    if len(candidates) > 1:
        raise Exception("More then one matching argument was found!")

    return candidates[0]


def get_action_from_gui() -> Option:
    import inquirer
    questions = [
        inquirer.List(
            "action",
            message="Select OIOIOI action",
            choices=COMMANDS
        )
    ]
    answers = inquirer.prompt(questions)
    return answers["action"]


def run_command(command) -> None:
    print('Running command', command)
    if not NO_INPUT:
        width = os.get_terminal_size().columns
        print('=' * width)
    sys.exit(os.WEXITSTATUS(os.system(command)))


def warn_user(action: Option) -> bool:
    print(f"You are going to execute command [{action.command}] marked as `dangerous`. Are you sure? [y/N]")
    while True:
        choice = input().lower()
        if not choice or "no".startswith(choice):
            return False
        elif "yes".startswith(choice):
            return True
        else:
            print("Please answer [yes] or [no].")


def run() -> None:
    action = get_action_from_args() or get_action_from_gui()
    action.fill_tty(disable=NO_INPUT)
    if action.warn and not NO_INPUT:
        if not warn_user(action):
            print("Aborting.")
            return
    run_command(f'{BASE_DOCKER_COMMAND} {action.command}')


def print_help() -> None:
    print("OIOIOI helper toolbox", "", "This script allows to control OIOIOI with Docker commands.",
          f"Commands are always being run with '{BASE_DOCKER_COMMAND}' prefix.",
          f"Aveliable commands are: ", "",
          *COMMANDS, "", "Example `build`:", f"{sys.argv[0]} build", sep="\n")


def main() -> None:
    try:
        check_commands()
        run()
    except Help:
        print_help()
    except Exception as e:
        print(f"An error occurred during execution: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
