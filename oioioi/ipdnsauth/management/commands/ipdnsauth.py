import csv

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from oioioi.ipdnsauth.models import DnsToUser, IpToUser


class Command(BaseCommand):
    help = (
        "Manages ipdnsauth module.\n"
        "First argument specifies, which bindings should be handled.\n"
        "Load/export format is simple csv-like 'user binding'.\n\n"
        "Options can be chained like this (ordering is ignored):\n"
        "manage.py ipdnsauth --export X.bak --unload X.old --load X.new"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            dest="clear",
            default=False,
            help="Clears all current bindings for ip/dns",
        )
        parser.add_argument(
            "--export",
            dest="exportfile",
            help="Exports current settings into FILE",
            metavar="FILE",
        )
        parser.add_argument(
            "--unload",
            dest="unloadfile",
            help="Deletes bindings from FILE.",
            metavar="FILE",
        )
        parser.add_argument("--load", dest="loadfile", help="Loads bindings from FILE.", metavar="FILE")
        parser.add_argument("model", type=str, choices=("ip", "dns"), help="Model")

    def _write(self, data, filename):
        with open(filename, "w") as csvfile:
            writer = csv.writer(csvfile, delimiter=" ", lineterminator="\n")
            for username, binding in data:
                writer.writerow([username, binding])

    def _read(self, filename):
        with open(filename) as csvfile:
            reader = csv.reader(csvfile, delimiter=" ")
            return [row for row in reader]

    def clear(self, module, modelMgr, *args):
        self.stderr.write("Clearing...\n")
        modelMgr.all().delete()

    def export_data(self, module, modelMgr):
        self.stderr.write("Exporting...\n")
        return [(row.user.username, str(row)) for row in modelMgr.all()]

    def export(self, module, modelMgr, filename):
        self._write(self.export_data(module, modelMgr), filename)

    def load_data(self, module, modelMgr, data):
        self.stderr.write("Loading...\n")
        for row in data:
            try:
                if module == "ip":
                    binding = IpToUser(user=User.objects.get(username=row[0]), ip_addr=row[1])
                elif module == "dns":
                    binding = DnsToUser(user=User.objects.get(username=row[0]), dns_name=row[1])
                binding.full_clean()
                binding.save()
            # pylint: disable=broad-except
            except Exception as e:
                self.stderr.write(f"Error for {row}: {e}\n")

    def load(self, module, modelMgr, filename):
        self.load_data(module, modelMgr, self._read(filename))

    def unload_data(self, module, modelMgr, data):
        self.stderr.write("Unloading...\n")
        for row in data:
            try:
                if module == "ip":
                    modelMgr.get(user__username=row[0], ip_addr=row[1]).delete()
                elif module == "dns":
                    modelMgr.get(user__username=row[0], dns_name=row[1]).delete()
            # pylint: disable=broad-except
            except Exception as e:
                self.stderr.write(f"Error for {row}: {e}\n")

    def unload(self, module, modelMgr, filename):
        self.unload_data(module, modelMgr, self._read(filename))

    def handle(self, *args, **options):
        command_map = {
            "exportfile": self.export,
            "clear": self.clear,
            "unloadfile": self.unload,
            "loadfile": self.load,
        }
        command_seq = ("exportfile", "clear", "unloadfile", "loadfile")

        if options["model"] == "ip":
            modelMgr = IpToUser.objects
        elif options["model"] == "dns":
            modelMgr = DnsToUser.objects

        for cmd in command_seq:
            if options[cmd]:
                command_map[cmd](options["model"], modelMgr, options[cmd])
