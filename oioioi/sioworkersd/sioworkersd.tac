from twisted.application import service, internet
from server import WorkerServerFactory

application = service.Application('sioworkersd')

internet.TCPServer(7888, WorkerServerFactory())\
        .setServiceParent(application)
