from __future__ import print_function

import os
import os.path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
from six.moves import input

from oioioi.base.utils.execute import ExecuteError, execute
from oioioi.filetracker.client import get_client

DEFAULT_SANDBOXES_MANIFEST = getattr(settings, 'SANDBOXES_MANIFEST',
    'http://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('-m', '--manifest', metavar='URL', dest='manifest_url',
                            default=DEFAULT_SANDBOXES_MANIFEST,
                            help="Specifies URL with the Manifest file listing available "
                                "sandboxes")
        parser.add_argument('-c', '--cache-dir', metavar='DIR', dest='cache_dir',
                            default=None,
                            help="Load cached sandboxes from a local directory")
        parser.add_argument('-d', '--download-dir', metavar='DIR', dest='download_dir',
                            default="sandboxes-download",
                            help="Temporary directory where the downloaded files will be "
                                "stored")
        parser.add_argument('--wget', metavar='PATH', dest='wget',
                            default="wget", help="Specifies the wget binary to use")
        parser.add_argument('-y', '--yes', dest='license_agreement', default=False,
                            action='store_true',
                            help="Enabling this options means that you agree to the license "
                                "terms and conditions, so no license prompt will be "
                                "displayed")
        parser.add_argument('-q', '--quiet', dest='quiet', default=False,
                            action='store_true',
                            help="Disables wget interactive progress bars")

    args = '[<sandbox-name> ...]'
    help = "Downloads sandboxes and stores them in the Filetracker."

    requires_model_validation = False

    def display_license(self, license):
        print("\nThe sandboxes are accompanied with a "
                "license:\n", file=self.stdout)
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
        print("--- Downloading Manifest ...", file=self.stdout)
        try:
            manifest_url = options['manifest_url']
            manifest = six.moves.urllib.request.urlopen(manifest_url).read()
            manifest = manifest.strip().splitlines()
        except Exception as e:
            raise CommandError("Error downloading manifest: %s" % (e,))

        print("--- Looking for license ...", file=self.stdout)
        try:
            license_url = six.moves.urllib.parse.urljoin(manifest_url,
                    'LICENSE')
            license = six.moves.urllib.request.urlopen(license_url).read()
            if not options['license_agreement']:
                self.display_license(license)
        except six.moves.urllib.error.HTTPError as e:
            if e.code != 404:
                raise

        if not args:
            args = manifest

        print("--- Preparing ...", file=self.stdout)
        urls = []
        cached_args = []
        for arg in args:
            basename = arg + '.tar.gz'
            if options['cache_dir']:
                path = os.path.join(options['cache_dir'], basename)
                if os.path.isfile(path):
                    cached_args.append(arg)
                    continue
            if arg not in manifest:
                raise CommandError("Sandbox '%s' not available (not in "
                        "Manifest)" % (arg,))
            urls.append(six.moves.urllib.parse.urljoin(manifest_url, basename))

        filetracker = get_client()

        download_dir = options['download_dir']
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        try:
            execute([options['wget'], '--version'])
        except ExecuteError:
            raise CommandError("Wget not working. Please specify a working "
                    "Wget binary using --wget option.")

        if len(urls) > 0:
            print("--- Downloading sandboxes ...", file=self.stdout)

            quiet_flag = ['-nv'] if options['quiet'] else []
            execute([options['wget'], '-N', '-i', '-'] + quiet_flag,
                    stdin='\n'.join(urls), capture_output=False,
                    cwd=download_dir)

        print("--- Saving sandboxes to the Filetracker ...", file=self.stdout)
        for arg in args:
            basename = arg + '.tar.gz'
            if arg in cached_args:
                local_file = os.path.join(options['cache_dir'], basename)
            else:
                local_file = os.path.join(download_dir, basename)
            print(" ", basename, file=self.stdout)
            filetracker.put_file('/sandboxes/' + basename, local_file)
            if arg not in cached_args:
                os.unlink(local_file)

        try:
            os.rmdir(download_dir)
        except OSError:
            print("--- Done, but couldn't remove the "
                    "downloads directory.", file=self.stdout)
        else:
            print("--- Done.", file=self.stdout)
