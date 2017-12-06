import BaseHTTPServer
import SocketServer
import logging
import cgi
import json

from django.db import transaction
from django.conf import settings
from django.core.management.base import BaseCommand

from oioioi.evalmgr.tasks import delay_environ


class ServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        # security through obscurity
        self.send_error(404)

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })
        if "data" not in form:
            self.send_error(404)
        else:
            logging.debug("Sioworkersd receiver got: " + form.getvalue('data'))
            env = json.loads(form.getvalue('data'))
            del env['workers_jobs']
            if 'workers_jobs.extra_args' in env:
                del env['workers_jobs.extra_args']
            assert 'workers_jobs.results' in env or 'error' in env

            with transaction.atomic():
                delay_environ(env)

            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('OK')


class Server(SocketServer.TCPServer):
    # See SIO-1741 and
    # https://docs.python.org/2/library/socketserver.html#SocketServer.BaseServer.allow_reuse_address
    allow_reuse_address = True


class Command(BaseCommand):
    def handle(self, *args, **options):
        Handler = ServerHandler
        httpd = Server((settings.SIOWORKERS_LISTEN_ADDR,
            settings.SIOWORKERS_LISTEN_PORT), Handler)
        httpd.serve_forever()
