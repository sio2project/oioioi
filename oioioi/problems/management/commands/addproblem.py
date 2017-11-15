import os.path
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from django.utils.module_loading import import_string
from django.db import transaction
from oioioi.problems.package import backend_for_package, NoBackend


class Command(BaseCommand):
    args = _("<filename>")
    help = _("Adds the problem from the given package to the database.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not args:
            raise CommandError(_("Missing argument (filename)"))
        if len(args) > 2:
            raise CommandError(_("Expected at most two arguments"))

        # The second argument can have only one value - 'nothrow'.
        # It's meant to be used in unit tests,
        # so that if adding the problem failed,
        # we can still investigate the problem package
        # and make sure that the errors there are what we expected.
        throw_on_problem_not_added = True
        if len(args) > 1:
            if args[1] == "nothrow":
                throw_on_problem_not_added = False
            else:
                raise CommandError(_("The second argument (if provided) "
                                     "can only have value 'nothrow'"
                                     " - to be used in testing"))

        filename = args[0]
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
