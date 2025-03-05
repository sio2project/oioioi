from __future__ import print_function

import os
import os.path

from django.core.management.base import BaseCommand

from oioioi.filetracker.client import get_client


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-d',
            '--sandboxes-dir',
            metavar='DIR',
            dest='sandboxes_dir',
            default=None,
            help="Load sandboxes from a local directory",
        )

    help = "Upload sandboxes to the Filetracker."

    def handle(self, *args, **options):
        filetracker = get_client()

        print("--- Saving sandboxes to the Filetracker ...", file=self.stdout)

        sandboxes_dir = os.fsencode(options['sandboxes_dir'])
        for file in os.listdir(sandboxes_dir):
            filename = os.fsdecode(file)
            if not filename.endswith(".tar.gz"):
                continue

            filetracker.put_file('/sandboxes/' + filename, os.path.join(options['sandboxes_dir'], filename))

        print("--- Done.", file=self.stdout)
