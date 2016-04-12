from optparse import make_option
import datetime
import time
import SocketServer
import threading
from dnslib import DNSRecord, DNSHeader, QTYPE, PTR, RR, A
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from oioioi.ipdnsauth.models import IpToUser
from oioioi.ipdnsauth.utils import username_to_hostname


logger = logging.getLogger(__name__)


# Most of the code taken from:
# https://gist.github.com/andreif/6069838


class BaseRequestHandler(SocketServer.BaseRequestHandler):

    def get_data(self):
        raise NotImplementedError

    def send_data(self, data):
        raise NotImplementedError

    def dns_response(self, data):
        request = DNSRecord.parse(data)

        logger.debug('%s', request)

        reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1),
                q=request.q)

        qname = request.q.qname
        qn = str(qname)
        if qn.endswith('.'):
            qn = qn[:-1]
        qtype = request.q.qtype
        qt = QTYPE[qtype]

        qnhost, qndomain = qn.split('.', 1)

        #
        # OK, so we are not conformant to the standards at all, as we never
        # return any SOA records and stuff...
        #

        if qndomain == settings.IPAUTH_DNSSERVER_DOMAIN:
            if qt in ['*', 'A']:
                for u in User.objects.filter(iptouser__isnull=False):
                    if qnhost == username_to_hostname(u.username):
                        for itu in u.iptouser_set.all():
                            reply.add_answer(RR(rname=qname, rtype=QTYPE.A,
                                rclass=1,
                                ttl=self.server.command.options['ttl'],
                                rdata=A(itu.ip_addr)))
        elif qn.endswith('.in-addr.arpa'):
            if qt in ['*', 'PTR']:
                qn = qn[:-len('.in-addr.arpa')]
                parts = qn.split('.')
                if len(parts) == 4:
                    ip = '.'.join(reversed(parts))
                    try:
                        iptu = IpToUser.objects.get(ip_addr=ip)
                        fqdn = username_to_hostname(iptu.user.username) + \
                                '.' + settings.IPAUTH_DNSSERVER_DOMAIN + '.'
                        reply.add_answer(RR(rname=qname, rtype=QTYPE.PTR,
                            rclass=1, ttl=self.server.command.options['ttl'],
                            rdata=PTR(fqdn)))
                    except IpToUser.DoesNotExist:
                        pass

        logger.debug('%s', reply)

        return reply.pack()

    def handle(self):
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        logger.debug("%s request %s (%s %s):", self.__class__.__name__[:3],
                now, self.client_address[0], self.client_address[1])
        try:
            data = self.get_data()
            logger.debug('%d %s', len(data), data.encode('hex'))
            self.send_data(self.dns_response(data))
        # pylint: disable=broad-except
        except Exception:
            logger.warning("Exception handling request", exc_info=True)


class TCPRequestHandler(BaseRequestHandler):
    def get_data(self):
        data = self.request.recv(8192).strip()
        sz = int(data[:2].encode('hex'), 16)
        if sz < len(data) - 2:
            raise Exception("Wrong size of TCP packet")
        elif sz > len(data) - 2:
            raise Exception("Too big TCP packet")
        return data[2:]

    def send_data(self, data):
        sz = hex(len(data))[2:].zfill(4).decode('hex')
        return self.request.sendall(sz + data)


class UDPRequestHandler(BaseRequestHandler):
    def get_data(self):
        return self.request[0].strip()

    def send_data(self, data):
        return self.request[1].sendto(data, self.client_address)


class UDPServer(SocketServer.ThreadingUDPServer):
    def __init__(self, command, *args, **kwargs):
        SocketServer.ThreadingUDPServer.__init__(self, *args, **kwargs)
        self.command = command


class TCPServer(SocketServer.ThreadingTCPServer):
    def __init__(self, command, *args, **kwargs):
        SocketServer.ThreadingTCPServer.__init__(self, *args, **kwargs)
        self.command = command


class Command(BaseCommand):
    help = "DNS server for ipdnsauth.\n\nAnswers DNS queries for names " \
        "and IP addresses managed by ipdnsauth module."

    option_list = BaseCommand.option_list + (
        make_option('--port', '-p',
                    type=int,
                    default=8053,
                    help="Specify port to listen on"),
        make_option('--bind-addr',
                    dest='bind_addr',
                    type=str,
                    default='',
                    help="IP address to bind the server"),
        make_option('--ttl',
                    type=int,
                    default=60,
                    help="Specify TTL for returned records"),
        )

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.options = None

    def handle(self, *args, **options):
        if not getattr(settings, 'IPAUTH_DNSSERVER_DOMAIN', None):
            raise CommandError("IPAUTH_DNSSERVER_DOMAIN not set in settings")
        self.options = options
        listen_addr = (options['bind_addr'], options['port'])
        servers = [
            ('udp', UDPServer(self, listen_addr, UDPRequestHandler)),
            ('tcp', TCPServer(self, listen_addr, TCPRequestHandler)),
        ]
        threads = []
        for name, s in servers:
            thread = threading.Thread(target=s.serve_forever,
                    name=('ipauth-dnsserver-' + name))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        while True:
            time.sleep(1)
        # Terminate the script in case both threads terminate
        for t in threads:
            t.join()
