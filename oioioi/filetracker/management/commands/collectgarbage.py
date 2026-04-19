import datetime

# import email.utils
import itertools
from concurrent.futures import ProcessPoolExecutor

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from filetracker.client import Client
from filetracker.utils import split_name

# import requests


client = Client(remote_url=settings.FILETRACKER_URL, local_store=None)


def set_client():
    global client
    client = Client(remote_url=settings.FILETRACKER_URL, local_store=None)


# Used for SZKOpuł filetracker health checks.
FILES_TO_KEEP = [
    "nagios_check.txt",
]
DIRS_TO_KEEP = [
    "sandboxes",
]


def keepfilter(filename):
    return filename.split("/")[0] in DIRS_TO_KEEP or filename in FILES_TO_KEEP


def delete_file(args):
    global client
    if args[2] > 1:
        print(" " + args[0])
    client.delete_file("/" + args[0] + "@" + str(args[1]))


def list_files_for_model(args):
    model = args[0]
    subpath = args[1]
    # Safety for multiprocessing.
    connections.close_all()
    file_fields = [field.name for field in model._meta.fields if field.get_internal_type() in ["FileField", "ImageField"]]
    if not file_fields:
        return []
    base_qs = model.objects.all()
    if len(file_fields) == 1:
        base_qs = base_qs.exclude(**{file_fields[0]: None})
        if subpath:
            base_qs = base_qs.filter(**{(file_fields[0] + "__startswith"): subpath})
    files = base_qs.values_list(*file_fields).distinct()
    return [split_name(file)[0] for file in itertools.chain.from_iterable(files) if file and file.startswith(subpath)]


class Command(BaseCommand):
    help = _("Delete all orphaned files older than specified number of days.")

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--days",
            action="store",
            type=int,
            dest="days",
            default=30,
            help=_("Orphaned files older than DAYS days will be deleted. Default value is 30."),
            metavar=_("DAYS"),
        )
        parser.add_argument(
            "-s",
            "--subpath",
            action="store",
            type=str,
            dest="subpath",
            default="",
            help=_("Restrict the cleaning to a filetracker subpath."),
            metavar=_("SUBPATH"),
        )
        parser.add_argument(
            "-n",
            "--paralell",
            action="store",
            type=int,
            dest="workers",
            default=0,
            help=_("How many files to delete in paralell."),
        )
        parser.add_argument(
            "-p",
            "--pretend",
            action="store_true",
            dest="pretend",
            default=False,
            help=_("If set, the orphaned files will only be displayed, not deleted."),
        )

    def _get_needed_files(self, subpath):
        models_list = [(model, subpath) for app in apps.get_app_configs() for model in app.get_models()]
        with ProcessPoolExecutor() as executor:
            results_list = executor.map(list_files_for_model, models_list)
        result = list(itertools.chain.from_iterable(results_list))
        return result

    # def get_ft_files(self, cutoff_timestamp, subpath):
    #    """Returns a list of paths"""
    #    ft_url = settings.FILETRACKER_URL
    #    url = ft_url + "/list/" + subpath.lstrip('/')
    #    rfc2822_date = email.utils.formatdate(cutoff_timestamp)
    #    response = requests.get(url, params={'last_modified': rfc2822_date})
    #    response.raise_for_status()
    #    result = response.content.decode('utf-8').split('\n')
    #    assert len(result.pop()) == 0
    #    return result

    def get_ft_files(self, cutoff_timestamp, subpath):
        subpath = "/" + subpath.lstrip("/")
        return client.list_remote_files(cutoff_timestamp, subpath, absolute_paths=True)

    def handle(self, *args, **options):
        assert options["workers"] >= 0
        max_date_to_delete = datetime.datetime.now() - datetime.timedelta(days=options["days"])
        cutoff_timestamp = int(max_date_to_delete.timestamp())
        print(_("Cutoff date is"), max_date_to_delete)
        print(_("Getting needed files..."))
        needed_files = self._get_needed_files(options["subpath"])
        print(_("Got needed files."))
        print(_("Getting list of files on filetracker..."))
        all_files = self.get_ft_files(cutoff_timestamp, options["subpath"])
        print(_("Got list of files on filetracker."))
        all_files = [f for f in all_files if not keepfilter(f)]
        to_delete = set(all_files) - set(needed_files)

        files_count = len(to_delete)
        if files_count == 0 and int(options["verbosity"]) > 0:
            print(_("No files to delete."))
        elif options["pretend"]:
            if int(options["verbosity"]) > 1:
                print(
                    ngettext(
                        "The following %d file is scheduled for deletion:",
                        "The following %d files are scheduled for deletion:",
                        files_count,
                    )
                    % files_count
                )
                for file in to_delete:
                    print(" ", file)
            elif int(options["verbosity"]) == 1:
                print(
                    ngettext(
                        "%d file scheduled for deletion.",
                        "%d files scheduled for deletion.",
                        files_count,
                    )
                    % files_count
                )
        else:
            if int(options["verbosity"]) > 1:
                print(
                    ngettext(
                        "Deleting the following %d file:",
                        "Deleting the following %d files:",
                        files_count,
                    )
                    % files_count
                )
            if int(options["verbosity"]) == 1:
                print(ngettext("Deleting %d file", "Deleting %d files", files_count) % files_count)
            if options["workers"] < 2:
                for file in to_delete:
                    delete_file((file, cutoff_timestamp, options["verbosity"]))
            else:
                print(_("Starting {workers} paralell workers.").format(workers=str(options["workers"])))
                with ProcessPoolExecutor(max_workers=options["workers"], initializer=set_client) as pool:
                    len([*pool.map(delete_file, [(file, cutoff_timestamp, options["verbosity"]) for file in to_delete])])
            print(_("Done."))
