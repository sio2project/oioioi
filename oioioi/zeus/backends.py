import json
import base64
import urllib2
import httplib
from urlparse import urljoin

from django.conf import settings
from django.db import transaction

from oioioi.base.utils import get_object_by_dotted_name
from oioioi.zeus.models import ZeusFetchSeq


zeus_language_map = {
    'cc': 'CPP',
    'cpp': 'CPP',
}


class ZeusError(StandardError):
    pass


class ZeusKeyError(ZeusError, KeyError):
    pass


def get_zeus_server(zeus_id):
    """Returns ZeusServer instance for ``zeus_id``."""
    server = settings.ZEUS_INSTANCES[zeus_id]
    # Used to inject mock instances/special handlers
    if server[0] == '__use_object__':
        return get_object_by_dotted_name(server[1])(zeus_id, server)
    return ZeusServer(zeus_id, server)


class Base64String(object):
    """String that needs to be encoded using base64 when serializing to JSON.
    """
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return str(self.string)

    def __unicode__(self):
        return unicode(self.string)

    def __eq__(self, other):
        return self.string == other.string


def _json_base64_encode(o):
    def _string_base64(s):
        if isinstance(s, Base64String):
            return base64.b64encode(str(s))
        raise TypeError
    return json.dumps(o, default=_string_base64, sort_keys=True)


def _json_base64_decode(o):
    def _dict_b64_decode(d):
        return {k: Base64String(base64.b64decode(v))
                if isinstance(v, (str, unicode)) else v
                for (k, v) in d.iteritems()}
    return json.loads(o, object_hook=_dict_b64_decode)


def _get_key(dictionary, key):
    if key not in dictionary:
        raise ZeusKeyError("Key %s not found in result" % key)
    return dictionary[key]


class ZeusServer(object):
    def __init__(self, zeus_id, server_info):
        self.url, user, passwd = server_info
        self.seq, _c = ZeusFetchSeq.objects.get_or_create(zeus_id=zeus_id)
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(None, self.url, user=user, passwd=passwd)
        self.opener = urllib2.build_opener(auth_handler)

    def _send(self, url, data=None, method='GET'):
        """Send the encoded ``data`` to given URL."""
        assert data is None or method == 'POST'
        if data is None:
            req = urllib2.Request(url=url)             # GET
        else:
            req = urllib2.Request(url=url, data=data)  # POST
        try:
            f = self.opener.open(req)
        except (urllib2.URLError, httplib.HTTPException) as e:
            raise ZeusError(e.reason)
        return f.getcode(), f.read()

    def _encode_and_send(self, url, data=None, method='GET'):
        """Encodes the ``data`` dictionary and sends it to the given URL."""
        json_data = _json_base64_encode(data) if data else None
        code, res = self._send(url, json_data, method)
        return code, _json_base64_decode(res)

    def send_regular(self, zeus_problem_id, kind, source_file, language):
        assert kind in 'INITIAL', 'NORMAL'
        assert language in zeus_language_map
        url = urljoin(self.url, 'problem/%d/job/%s/' % (zeus_problem_id, kind))
        with source_file as f:
            data = {
                'source_code': Base64String(f.read()),
                'language': Base64String(zeus_language_map[language]),
            }
        code, res = self._encode_and_send(url, data, method='POST')
        if code != 200:
            raise ZeusError(res.get('error', None), code)
        return _get_key(res, 'check_uid')

    def send_testrun(self, zeus_problem_id, source_file, language, input_file,
                     library_file):
        assert language in zeus_language_map
        url = urljoin(self.url, 'problem/%d/job/TESTRUN/' % zeus_problem_id)

        with source_file as src:
            with input_file as inp:
                data = {
                    'source_code': Base64String(src.read()),
                    'input_test': Base64String(inp.read()),
                    'language': Base64String(zeus_language_map[language]),
                }
                if library_file is not None:
                    with library_file as lib:
                        data.update({'library': Base64String(lib.read())})

        code, res = self._encode_and_send(url, data, method='POST')
        if code != 200:
            raise ZeusError(res.get('error', None), code)
        return _get_key(res, 'check_uid')

    def fetch_results(self):
        """Fetches the results from remote server.
           This operation may be blocking.
        """
        url = urljoin(self.url, 'reports_since/%d/' % self.seq.next_seq)
        code, res = self._encode_and_send(url)
        if code != 200:
            raise ZeusError(res.get('error', None), code)
        return _get_key(res, 'next_seq'), _get_key(res, 'reports')

    @transaction.commit_on_success
    def commit_fetch(self, seq):
        """Shall be called after calling fetch_results, if all results have
           been saved successfully.

           ``seq`` - as returned by fetch_results
        """
        self.seq.next_seq = seq
        self.seq.save()

    def download_output(self, output_id):
        """Downloads and returns file containing stdout for test run."""
        url = urljoin(self.url, 'full_stdout/%d/' % output_id)
        code, res = self._encode_and_send(url)
        if code != 200:
            raise ZeusError(res.get('error', None), code)
        return _get_key(res, 'full_stdout')
