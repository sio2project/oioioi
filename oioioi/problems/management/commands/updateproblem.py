import os.path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.module_loading import import_string
from django.utils.translation import ugettext as _

from oioioi.problems.models import Problem
from oioioi.problems.package import NoBackend, backend_for_package


class Command(BaseCommand):
    help = _("Updates an existing problem using the given package file.")

    def add_arguments(self, parser):
        parser.add_argument('problem_id', type=int)
        parser.add_argument('filename', type=str)

    @transaction.atomic
    def handle(self, *args, **options):
        problem_id = options['problem_id']
        filename = options['filename']
        if not os.path.exists(filename):
            raise CommandError(_("File not found: ") + filename)

        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            raise CommandError(_("Problem #%d does not exist") % (problem_id,))

        try:
            backend = import_string(backend_for_package(filename))()
        except NoBackend:
            raise CommandError(_("Package format not recognized"))

        problem = backend.simple_unpack(filename, existing_problem=problem)
