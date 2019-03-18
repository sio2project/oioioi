import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.module_loading import import_string
from django.utils.translation import ugettext as _

from oioioi.problems.package import NoBackend, backend_for_package


class Command(BaseCommand):
    help = _("Adds the problem from the given package to the database.")

    def add_arguments(self, parser):
        parser.add_argument('filename',
                            type=str)
        parser.add_argument('no_throw',
                            type=str,
                            nargs='?',
                            default='',
                            choices=['', 'nothrow'])

    @transaction.atomic
    def handle(self, *args, **options):
        # The second argument can have only one value - 'nothrow'.
        # It's meant to be used in unit tests,
        # so that if adding the problem failed,
        # we can still investigate the problem package
        # and make sure that the errors there are what we expected.
        throw_on_problem_not_added = True
        if options['no_throw']:
            throw_on_problem_not_added = False

        filename = options['filename']
        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)
        try:
            backend = \
                    import_string(backend_for_package(filename))()
        except NoBackend:
            raise CommandError(_("Package format not recognized"))

        problem = backend.simple_unpack(filename)
        if problem is not None:
            self.stdout.write('%d\n' % (problem.id,))
        elif throw_on_problem_not_added:
            raise CommandError(_("There was an error adding the problem"))
