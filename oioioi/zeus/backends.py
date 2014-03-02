from django.conf import settings
from oioioi.base.utils import get_object_by_dotted_name


def get_zeus_server(server):
    """Returns ZeusServer instance for ``server``.

       If ``server`` is not a list/tuple, then it's fetched from settings.
    """
    if not isinstance(server, (list, tuple)):
        server = settings.ZEUS_INSTANCES[server]
    # Used to inject mock instances/special handlers
    if server[0] == '__use_object__':
        return get_object_by_dotted_name(server[1])
    return ZeusServer(server)


class ZeusServer(object):
    def __init__(self, server_info):
        self.url, self.login, self.secret = server_info

    def _send(self, url, data, method='GET'):
        """Encodes the ``data`` dictionary and sends it to given URL."""
        raise NotImplementedError

    def send_regular(self, kind, source_file, language):
        raise NotImplementedError

    def send_testrun(self, source_file, language, input_file, library_file):
        raise NotImplementedError

    def fetch_results(self):
        """Fetches the results from remote server.
           This operation may be blocking.
        """
        raise NotImplementedError

    def download_output(self, output_id):
        """Downloads and returns file containing stdout for test run."""
        raise NotImplementedError
