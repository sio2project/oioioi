from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.filetracker.client import get_client
from optparse import make_option
import os, os.path
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
    )

    args = '[<sandbox-name> ...]'
    help = "Downloads sandboxes and stores them in the Filetracker."

    requires_model_validation = False

    def handle(self, *args, **options):
        print >>self.stdout, "--- Downloading Manifest ..."
        try:
            manifest_url = options['manifest_url']
            manifest = urllib2.urlopen(manifest_url).read()
            manifest = manifest.strip().splitlines()
        except Exception, e:
            raise CommandError("Error downloading manifest: %s" % (e,))

        if not args:
            args = manifest

        print >>self.stdout, "--- Preparing ..."
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

        print >>self.stdout, "--- Downloading sandboxes ..."
        execute([options['wget'], '-N', '-i', '-'], stdin='\n'.join(urls),
                capture_output=False, cwd=dir)

        print >>self.stdout, "--- Saving sandboxes to the Filetracker ..."
        for arg in args:
            basename = arg + '.tar.gz'
            local_file = os.path.join(dir, basename)
            print >>self.stdout, " ", basename
            filetracker.put_file('/sandboxes/' + basename, local_file)
            os.unlink(local_file)

        try:
            os.rmdir(dir)
        except OSError:
            print >>self.stdout, "--- Done, but couldn't remove the " \
                    "downloads directory."
        else:
            print >>self.stdout, "--- Done."
