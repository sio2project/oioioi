from __future__ import print_function

import os
import os.path
from subprocess import check_output

import urllib.error
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from oioioi.base.utils.execute import ExecuteError, execute
from oioioi.filetracker.client import get_client

DEFAULT_SANDBOXES_MANIFEST = getattr(
    settings,
    'SANDBOXES_MANIFEST',
    'https://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest',
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-m',
            '--manifest',
            metavar='URL',
            dest='manifest_url',
            default=DEFAULT_SANDBOXES_MANIFEST,
            help="Specifies URL with the Manifest file listing available sandboxes",
        )
        parser.add_argument(
            '-c',
            '--cache-dir',
            metavar='DIR',
            dest='cache_dir',
            default=None,
            help="Load cached sandboxes from a local directory",
        )
        parser.add_argument(
            '-d',
            '--download-dir',
            metavar='DIR',
            dest='download_dir',
            default="sandboxes-download",
            help="Temporary directory where the downloaded files will be stored",
        )
        parser.add_argument(
            '--wget',
            metavar='PATH',
            dest='wget',
            default="wget",
            help="Specifies the wget binary to use",
        )
        parser.add_argument(
            '-y',
            '--yes',
            dest='license_agreement',
            default=False,
            action='store_true',
            help="Enabling this options means that you agree to the license "
                 "terms and conditions, so no license prompt will be "
                 "displayed",
        )
        parser.add_argument(
            '-q',
            '--quiet',
            dest='quiet',
            default=False,
            action='store_true',
            help="Disables wget interactive progress bars",
        )
        parser.add_argument(
            '-p',
            '--script-path',
            metavar='FILEPATH',
            dest='script_path',
            default=None,
            help="Path to script that downloads the sandboxes",
        )
        parser.add_argument(
            'sandboxes', type=str, nargs='*', help='List of sandboxes to be downloaded'
        )

    help = "Downloads sandboxes and stores them in the Filetracker."

    requires_model_validation = False

    def display_license(self, license):
        print("\nThe sandboxes are accompanied with a license:\n", file=self.stdout)
        self.stdout.write(license)
        msg = "\nDo you accept the license? (yes/no):"
        confirm = input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'no':
                raise CommandError("License not accepted")
            break

    def handle(self, *args, **options):
        if not options.get('script_path'):
            raise CommandError("You must specify a script path")

        license_agreement = ""
        if options['license_agreement']:
            license_agreement = "-y"
        cache_dir = "-c "
        if options['cache_dir']:
            cache_dir += options['cache_dir']

        args_str = " ".join(args)
        manifest_output = check_output(
            f"{options['script_path']} -m {options['manifest_url']} -d {options['download_dir']} --wget {options['wget']} -q {license_agreement} {cache_dir} {args_str}",
            shell=True, text=True)
        if manifest_output == "":
            raise CommandError(f"Manifest output cannot be empty")

        manifest = manifest_output.strip().splitlines()
        args = options['sandboxes']
        if not args:
            args = manifest

        print("--- Preparing to save sandboxes to the Filetracker ...", file=self.stdout)
        cached_args = [
            arg for arg in args
            if options['cache_dir'] and os.path.isfile(os.path.join(options['cache_dir'], arg + '.tar.gz'))
        ]

        filetracker = get_client()

        print("--- Saving sandboxes to the Filetracker ...", file=self.stdout)
        for arg in args:
            basename = arg + '.tar.gz'
            if arg in cached_args:
                local_file = os.path.join(options['cache_dir'], basename)
            else:
                local_file = os.path.join(options['download_dir'], basename)
            filetracker.put_file('/sandboxes/' + basename, local_file)
            if arg not in cached_args:
                os.unlink(local_file)

        try:
            os.rmdir(options['download_dir'])
        except OSError:
            print(
                "--- Done, but couldn't remove the downloads directory.",
                file=self.stdout,
            )
        else:
            print("--- Done.", file=self.stdout)
