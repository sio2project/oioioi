from twisted.internet.protocol import ServerFactory
from sio.protocol import rpc


class WorkerServer(rpc.WorkerRPC):
    def __init__(self):
        rpc.WorkerRPC.__init__(self, server=True)
        self.ready.addCallback(self.established)

    def established(self, ignore=None):
        print 'Worker %s connected' % str(self.transport.getPeer())


class WorkerServerFactory(ServerFactory):
    protocol = WorkerServer
