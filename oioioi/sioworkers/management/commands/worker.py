import json
from xmlrpclib import Server

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    args = '<command> [args]'   # TODO
    help = 'TODO'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.server = Server(settings.SIOWORKERSD_URL)

    def cmd_list(self, **kwargs):
        l = self.server.get_workers()
        if l:
            self.stdout.write('\n'.join(map(str, l)))
        else:
            self.stdout.write('No workers connected.\n')

    def cmd_run(self, *args, **kwargs):
        if len(args) != 1:
            self.stdout.write("Required exactly one argument - job env.\n")
            return
        self.stdout.write(self.server.run_group(json.dumps({
            "workers_jobs": {
                "worker.py-task": json.loads(args[0]),
            }
        })))

    def cmd_sync_run(self, *args, **kwargs):
        if len(args) != 1:
            self.stdout.write("Required exactly one argument - job env.\n")
            return
        self.stdout.write(repr(self.server.sync_run_group(json.dumps({
            "workers_jobs": {
                "worker.py-task": json.loads(args[0]),
            }
        }))))

    def cmd_run_group(self, *args, **kwargs):
        if len(args) != 1:
            self.stdout.write("Required exactly one argument - job env.\n")
            return
        self.stdout.write(self.server.run_group(args[0]))

    def cmd_sync_run_group(self, *args, **kwargs):
        if len(args) != 1:
            self.stdout.write("Required exactly one argument - job env.\n")
            return
        self.stdout.write(repr(self.server.sync_run_group(args[0])))

    def cmd_queue(self, *args, **kwargs):
        q = self.server.get_queue()
        if not q:
            self.stdout.write('Empty queue.\n')
            return
        self.stdout.write(unicode(q).encode('utf-8'))

    def handle(self, *args, **kwargs):
        if not args:
            cmds = [i[4:] for i in dir(self) if i.startswith('cmd_')]
            self.stdout.write('Available commands: %s\n' % ', '.join(cmds))
            return
        cmd = args[0]
        args = args[1:]
        try:
            f = getattr(self, 'cmd_' + cmd)
        except AttributeError:
            raise CommandError('Invalid command: %s' % cmd)
        f(*args, **kwargs)
