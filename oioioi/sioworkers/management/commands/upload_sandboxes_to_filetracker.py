from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from django.core.management.base import BaseCommand

from oioioi.filetracker.client import get_client


def upload_sandbox(file):
    filetracker = get_client()
    filetracker.put_file("/sandboxes/" + file.name, str(file))


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--sandboxes-dir",
            metavar="DIR",
            dest="sandboxes_dir",
            default=None,
            help="Load sandboxes from a local directory",
        )

    help = "Upload sandboxes to the Filetracker."


    def handle(self, *args, **options):
        print("--- Saving sandboxes to the Filetracker ...", file=self.stdout)

        sandboxes_dir = Path(options["sandboxes_dir"])
        with ProcessPoolExecutor() as executor:
            executor.map(upload_sandbox, sandboxes_dir.glob('*.tar.gz'))

        print("--- Done.", file=self.stdout)
