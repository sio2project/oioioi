from django.conf import settings
from django.core.management.base import BaseCommand
import oioioi
import BaseHTTPServer
import SocketServer
import logging
import cgi
import json


class ServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        #security through obscurity
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
            assert 'workers_jobs.results' in env
            oioioi.evalmgr.evalmgr_job.delay(env)
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('OK')


class Command(BaseCommand):
    def handle(self, *args, **options):
        Handler = ServerHandler
        httpd = SocketServer.TCPServer((settings.SIOWORKERS_LISTEN_ADDR,
            settings.SIOWORKERS_LISTEN_PORT), Handler)
        httpd.serve_forever()
