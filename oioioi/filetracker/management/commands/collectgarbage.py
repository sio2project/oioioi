from __future__ import print_function

import datetime
import itertools

from django.core.management.base import BaseCommand
from django.db.models.loading import cache
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext
from filetracker.utils import split_name

from oioioi.filetracker.client import get_client


class Command(BaseCommand):
    help = _("Delete all orphaned files older than specified number of days.")

    def add_arguments(self, parser):
        parser.add_argument(
            '-d',
            '--days',
            action='store',
            type=int,
            dest='days',
            default=30,
            help=_(
                "Orphaned files older than DAYS days will "
                "be deleted. Default value is 30."
            ),
            metavar=_("DAYS"),
        )
        parser.add_argument(
            '-p',
            '--pretend',
            action='store_true',
            dest='pretend',
            default=False,
            help=_(
                "If set, the orphaned files will only be displayed, not deleted."
            ),
        )

    def _get_needed_files(self):
        result = []
        for app in cache.get_apps():
            model_list = cache.get_models(app)
            for model in model_list:
                file_fields = [
                    field.name
                    for field in model._meta.fields
                    if field.get_internal_type() == 'FileField'
                ]

                if len(file_fields) > 0:
                    files = model.objects.all().values_list(*file_fields)
                    result.extend(
                        [
                            split_name(file)[0]
                            for file in itertools.chain.from_iterable(files)
                            if file
                        ]
                    )
        return result

    def handle(self, *args, **options):
        needed_files = self._get_needed_files()
        all_files = get_client().list_local_files()
        max_date_to_delete = datetime.datetime.now() - datetime.timedelta(
            days=options['days']
        )

        diff = set([f[0] for f in all_files]) - set(needed_files)
        to_delete = [
            f[0]
            for f in all_files
            if f[0] in diff
            and datetime.datetime.fromtimestamp(f[1]) < max_date_to_delete
        ]

        files_count = len(to_delete)
        if files_count == 0 and int(options['verbosity']) > 0:
            print(_("No files to delete."))
        elif options['pretend']:
            if int(options['verbosity']) > 1:
                print(
                    ungettext(
                        "The following %d file is scheduled for deletion:",
                        "The following %d files are scheduled for deletion:",
                        files_count,
                    )
                    % files_count
                )
                for file in to_delete:
                    print(" ", file)
            elif int(options['verbosity']) == 1:
                print(
                    ungettext(
                        "%d file scheduled for deletion.",
                        "%d files scheduled for deletion.",
                        files_count,
                    )
                    % files_count
                )
        else:
            if int(options['verbosity']) > 1:
                print(
                    ungettext(
                        "Deleting the following %d file:",
                        "Deleting the following %d files:",
                        files_count,
                    )
                    % files_count
                )
            if int(options['verbosity']) == 1:
                print(
                    ungettext("Deleting %d file", "Deleting %d files", files_count)
                    % files_count
                )
            for file in to_delete:
                if int(options['verbosity']) > 1:
                    print(" ", file)
                get_client().delete_file('/' + file)
