from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from oioioi.problems.package import backend_for_package
import os.path


class Command(BaseCommand):
    args = _("<filename>")
    help = _("Adds the problem from the given package to the database.")

    def handle(self, *args, **options):
        if not args:
            raise CommandError(_("Missing argument (filename)"))
        if len(args) > 1:
            raise CommandError(_("Expected only one argument"))

        filename = args[0]
        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        try:
            backend = backend_for_package(filename)
        except NoBackend:
            raise CommandError(_("Package format not recognized"))

        problem = backend.unpack(filename)
        self.stdout.write('%d\n' % (problem.id,))
