from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from oioioi.problems.models import Problem
from oioioi.problems.package import backend_for_package, NoBackend
import os.path


class Command(BaseCommand):
    args = _("<problem_id> <filename>")
    help = _("Updates an existing problem using the given package file.")

    def handle(self, *args, **options):
        if len(args) < 2:
            raise CommandError(_("Not enough arguments"))
        if len(args) > 2:
            raise CommandError(_("Too many arguments"))

        try:
            problem_id = int(args[0])
        except ValueError:
            raise CommandError(_("Invalid problem id: ") + args[0])

        filename = args[1]
        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            raise CommandError(_("Problem #%d does not exist") % (problem_id,))

        try:
            backend = backend_for_package(filename)
        except NoBackend:
            raise CommandError(_("Package format not recognized"))

        problem = backend.unpack(filename, existing_problem=problem)
