from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from jsonrpclib import Server
import json


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
        env = json.loads(' '.join(args))
        self.stdout.write(self.server.run(env, 0))

    def cmd_queue(self, *args, **kwargs):
        if int(kwargs['verbosity']) > 1:
            verbose = True
        else:
            verbose = False
        q = self.server.get_queue(verbose)
        if not q:
            self.stdout.write('Empty queue.\n')
            return
        self.stdout.write('\n'.join(map(str, q)))

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
