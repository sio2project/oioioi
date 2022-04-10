# Taken from
# https://github.com/django-extensions/django-extensions/blob/master/django_extensions/management/commands/shell_plus.py
# django_extensions/management/commands/shell_plus.py
# pylint: skip-file

from __future__ import print_function

import os
import time

from django.core.management.base import BaseCommand
from django_extensions.management.shells import import_objects


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--plain',
            action='store_true',
            dest='plain',
            help='Tells Django to use plain Python, not BPython nor IPython.',
        )
        parser.add_argument(
            '--bpython',
            action='store_true',
            dest='bpython',
            help='Tells Django to use BPython, not IPython.',
        )
        parser.add_argument(
            '--ipython',
            action='store_true',
            dest='ipython',
            help='Tells Django to use IPython, not BPython.',
        )
        parser.add_argument(
            '--notebook',
            action='store_true',
            dest='notebook',
            help='Tells Django to use IPython args.',
        )
        parser.add_argument(
            '--no-pythonrc',
            action='store_true',
            dest='no_pythonrc',
            help='Tells Django not to execute PYTHONSTARTUP file',
        )
        parser.add_argument(
            '--print-sql',
            action='store_true',
            default=False,
            help="Print SQL queries as they're executed",
        )
        parser.add_argument(
            '--dont-load',
            action='append',
            dest='dont_load',
            default=[],
            help='Ignore autoloading of some apps/models. Can be used several times.',
        )
        parser.add_argument(
            '--quiet-load',
            action='store_true',
            default=False,
            dest='quiet_load',
            help='Do not display loaded models messages',
        )

    help = "Like the 'shell' command but autoloads the models of all installed Django apps."

    requires_model_validation = True

    def handle(self, *args, **options):
        use_notebook = options.get('notebook', False)
        use_ipython = options.get('ipython', False)
        use_bpython = options.get('bpython', False)
        use_plain = options.get('plain', False)
        use_pythonrc = not options.get('no_pythonrc', True)

        if options.get("print_sql", False):
            # Code from http://gist.github.com/118990
            from django.db.backends import util

            sqlparse = None
            try:
                import sqlparse
            except ImportError:
                pass

            class PrintQueryWrapper(util.CursorDebugWrapper):
                def execute(self, sql, params=()):
                    starttime = time.time()
                    try:
                        return self.cursor.execute(sql, params)
                    finally:
                        execution_time = time.time() - starttime
                        raw_sql = self.db.ops.last_executed_query(
                            self.cursor, sql, params
                        )
                        if sqlparse:
                            print(sqlparse.format(raw_sql, reindent=True))
                        else:
                            print(raw_sql)
                        print()
                        print(
                            'Execution time: %.6fs [Database: %s]'
                            % (execution_time, self.db.alias)
                        )
                        print()

            util.CursorDebugWrapper = PrintQueryWrapper

        def run_notebook():
            from django.conf import settings
            from IPython.frontend.html.notebook import notebookapp

            app = notebookapp.NotebookApp.instance()
            ipython_arguments = getattr(
                settings,
                'IPYTHON_ARGUMENTS',
                ['--ext', 'django_extensions.management.notebook_extension'],
            )
            app.initialize(ipython_arguments)
            app.start()

        def run_plain():
            # Using normal Python shell
            import code

            imported_objects = import_objects(options, self.style)
            try:
                # Try activating rlcompleter, because it's handy.
                import readline
            except ImportError:
                pass
            else:
                # We don't have to wrap the following import in a 'try', because
                # we already know 'readline' was imported successfully.
                import rlcompleter

                readline.set_completer(rlcompleter.Completer(imported_objects).complete)
                readline.parse_and_bind("tab:complete")

            # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
            # conventions and get $PYTHONSTARTUP first then import user.
            if use_pythonrc:
                pythonrc = os.environ.get("PYTHONSTARTUP")
                if pythonrc and os.path.isfile(pythonrc):
                    try:
                        exec(
                            compile(open(pythonrc).read(), pythonrc, 'exec'),
                            globals(),
                            locals(),
                        )
                    except NameError:
                        pass
            code.interact(local=imported_objects)

        def run_bpython():
            from bpython import embed

            imported_objects = import_objects(options, self.style)
            embed(imported_objects)

        def run_ipython():
            try:
                from IPython import embed

                imported_objects = import_objects(options, self.style)
                embed(user_ns=imported_objects)
            except ImportError:
                # IPython < 0.11
                # Explicitly pass an empty list as arguments, because otherwise
                # IPython would use sys.argv from this script.
                # Notebook not supported for IPython < 0.11.
                from IPython.Shell import IPShell

                imported_objects = import_objects(options, self.style)
                shell = IPShell(argv=[], user_ns=imported_objects)
                shell.mainloop()

        if use_notebook:
            run_notebook()
        elif use_plain:
            run_plain()
        elif use_ipython:
            run_ipython()
        elif use_bpython:
            run_bpython()
        else:
            for func in (run_bpython, run_ipython, run_plain):
                try:
                    func()
                except ImportError:
                    continue
                else:
                    break
            else:
                import traceback

                traceback.print_exc()
                print(
                    self.style.ERROR(
                        "Could not load any interactive Python environment."
                    )
                )
