from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.filetracker.client import get_client
from optparse import make_option
import os
import os.path
import urllib2
import urlparse

DEFAULT_SANDBOXES_MANIFEST = getattr(settings, 'SANDBOXES_MANIFEST',
    'http://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest')


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-m', '--manifest', metavar='URL', dest='manifest_url',
            default=DEFAULT_SANDBOXES_MANIFEST,
            help="Specifies URL with the Manifest file listing available "
                "sandboxes"),
        make_option('-d', '--download-dir', metavar='DIR', dest='download_dir',
            default="sandboxes-download",
            help="Temporary directory where the downloaded files will be "
                "stored"),
        make_option('--wget', metavar='PATH', dest='wget',
            default="wget", help="Specifies the wget binary to use"),
        make_option('-y', '--yes', dest='license_agreement', default=False,
            action='store_true',
            help="Enabling this options means that you agree to the license "
                "terms and conditions, so no license prompt will be "
                "displayed"),
    )

    args = '[<sandbox-name> ...]'
    help = "Downloads sandboxes and stores them in the Filetracker."

    requires_model_validation = False

    def display_license(self, license):
        print >> self.stdout, "\nThe sandboxes are accompanied with a " \
                "license:\n"
        self.stdout.write(license)
        msg = "\nDo you accept the license? (yes/no):"
        confirm = raw_input(msg)
        while 1:
            if confirm not in ('yes', 'no'):
                confirm = raw_input('Please enter either "yes" or "no": ')
                continue
            if confirm == 'no':
                raise CommandError("License not accepted")
            break

    def handle(self, *args, **options):
        print >> self.stdout, "--- Downloading Manifest ..."
        try:
            manifest_url = options['manifest_url']
            manifest = urllib2.urlopen(manifest_url).read()
            manifest = manifest.strip().splitlines()
        except Exception, e:
            raise CommandError("Error downloading manifest: %s" % (e,))

        print >> self.stdout, "--- Looking for license ..."
        try:
            license_url = urlparse.urljoin(manifest_url, 'LICENSE')
            license = urllib2.urlopen(license_url).read()
            if not options['license_agreement']:
                self.display_license(license)
        except urllib2.HTTPError, e:
            if e.code != 404:
                raise

        if not args:
            args = manifest

        print >> self.stdout, "--- Preparing ..."
        urls = []
        for arg in args:
            if arg not in manifest:
                raise CommandError("Sandbox '%s' not available (not in "
                        "Manifest)" % (arg,))
            urls.append(urlparse.urljoin(manifest_url, arg + '.tar.gz'))

        filetracker = get_client()

        dir = options['download_dir']
        if not os.path.exists(dir):
            os.makedirs(dir)

        try:
            execute([options['wget'], '--version'])
        except ExecuteError:
            raise CommandError("Wget not working. Please specify a working "
                    "Wget binary using --wget option.")

        print >> self.stdout, "--- Downloading sandboxes ..."
        execute([options['wget'], '-N', '-i', '-'], stdin='\n'.join(urls),
                capture_output=False, cwd=dir)

        print >> self.stdout, "--- Saving sandboxes to the Filetracker ..."
        for arg in args:
            basename = arg + '.tar.gz'
            local_file = os.path.join(dir, basename)
            print >> self.stdout, " ", basename
            filetracker.put_file('/sandboxes/' + basename, local_file)
            os.unlink(local_file)

        try:
            os.rmdir(dir)
        except OSError:
            print >> self.stdout, "--- Done, but couldn't remove the " \
                    "downloads directory."
        else:
            print >> self.stdout, "--- Done."
