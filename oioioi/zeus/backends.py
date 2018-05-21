from __future__ import print_function

import base64
import json
import logging
import pprint
import time

from django.conf import settings
from django.utils.module_loading import import_string
from six.moves import range
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
import six.moves.http_client

logger = logging.getLogger(__name__)

zeus_language_map = {
    'c': 'C',
    'cc': 'CPP',
    'cpp': 'CPP',
}


class ZeusError(Exception):
    pass


class ZeusKeyError(ZeusError, KeyError):
    pass


def get_zeus_server(zeus_id):
    """Returns ZeusServer instance for ``zeus_id``."""
    server = settings.ZEUS_INSTANCES[zeus_id]
    # Used to inject mock instances/special handlers
    if server[0] == '__use_object__':
        return import_string(server[1])(zeus_id, server[2])
    return ZeusServer(zeus_id, server)


class Base64String(object):
    """String that needs to be encoded using base64 when serializing to JSON.
    """
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return str(self.string)

    def __unicode__(self):
        return six.text_type(self.string)

    def __repr__(self):
        return 'Base64String(%s)' % self.string

    def __eq__(self, other):
        return self.string == other.string


def _json_base64_encode(o):
    def _string_base64(s):
        if isinstance(s, Base64String):
            return base64.b64encode(str(s))
        raise TypeError
    return json.dumps(o, default=_string_base64, sort_keys=True)


def _json_base64_decode(o, wrap=False):
    def _dict_b64_decode(d):
        return {k: (Base64String(base64.b64decode(v)) if wrap
                else base64.b64decode(v)) if isinstance(v, six.string_types)
                else v for (k, v) in six.iteritems(d)}
    return json.loads(o, object_hook=_dict_b64_decode)


def _get_key(dictionary, key):
    if key not in dictionary:
        raise ZeusKeyError("Key %s not found in result" % key)
    return dictionary[key]


class EagerHTTPBasicAuthHandler(six.moves.urllib.request.BaseHandler):
    def __init__(self, user, passwd):
        cred = '%s:%s' % (user, passwd)
        self.auth_string = 'Basic %s' % base64.b64encode(cred)

    def http_open(self, req):
        assert isinstance(req, six.moves.urllib.request.Request), \
                ("Incorrect request type: %s" % type(req))
        if 'Authorization' not in req.headers:
            req.add_header('Authorization', self.auth_string)

    def https_open(self, req):
        self.http_open(req)


class ZeusServer(object):
    def __init__(self, zeus_id, server_info):
        self.url, user, passwd = server_info
        auth_handler = EagerHTTPBasicAuthHandler(user, passwd)
        self.opener = six.moves.urllib.request.build_opener(auth_handler,
                six.moves.urllib.request.HTTPSHandler())

    def _send(self, url, data=None, retries=None, **kwargs):
        """Send the encoded ``data`` to given URL."""
        timeout = getattr(settings, 'ZEUS_CONNECTION_TIMEOUT', 60)
        retries = retries or getattr(settings, 'ZEUS_SEND_RETRIES', 3)
        retry_sleep = getattr(settings, 'ZEUS_RETRY_SLEEP', 1)

        assert retries > 0

        req = six.moves.urllib.request.Request(url=url, data=data)  # POST

        for i in range(retries):
            try:
                f = self.opener.open(req, timeout=timeout)
                return f.getcode(), f.read()
            except six.moves.urllib.error.HTTPError as e:
                # Custom format for HTTPError,
                # as default does not say anything.
                fmt, args = "HTTPError(%s): %s", (str(e.code), str(e.reason))
                logger.error(fmt, *args)
                if i == retries-1:
                    raise ZeusError(type(e), fmt % args)
            except (six.moves.urllib.error.URLError,
                    six.moves.http_client.HTTPException) as e:
                logger.error("%s exception while querying %s", url, type(e),
                             exc_info=True)
                if i == retries-1:
                    raise ZeusError(type(e), e)
            time.sleep(retry_sleep)

    def _encode_and_send(self, url, data=None, **kwargs):
        """Encodes the ``data`` dictionary and sends it to the given URL."""

        assert data is not None
        json_data = _json_base64_encode(data)
        code, res = self._send(url, json_data, **kwargs)
        decoded_res = _json_base64_decode(res)

        logger.info("Received response with code=%d: %s", code,
                pprint.pformat(decoded_res, indent=2))
        return code, decoded_res

    def send_regular(self, zeus_problem_id, kind, source_code, language,
                     submission_id, return_url):
        assert kind in ('INITIAL', 'NORMAL'), ("Invalid kind: %s" % kind)
        assert language in zeus_language_map, \
                ("Invalid language: %s" % language)
        url = six.moves.urllib.parse.urljoin(self.url,
                    'dcj_problem/%d/submissions' % (zeus_problem_id,))
        data = {
            'submission_type': Base64String('SMALL' if kind == 'INITIAL'
                                            else 'LARGE'),
            'return_url': Base64String(return_url),
            'username': Base64String(submission_id),  # not used by zeus,
            # only for debugging
            'metadata': Base64String('HASTA LA VISTA, BABY'),  # not used
            # by zeus, but zeus sends back meaningful metadata
            'source_code': Base64String(source_code),
            'language': Base64String(zeus_language_map[language]),
        }
        code, res = self._encode_and_send(url, data)
        if code != 200:
            raise ZeusError(res.get('error', None), code)
        return _get_key(res, 'submission_id')


class ZeusTestServer(ZeusServer):
    """ Useful for manual debugging
        In order to use it, add:

        'mock_server': ('__use_object__',
                           'oioioi.zeus.backends.ZeusTestServer',
                           ('', '', '')),

        to your ZEUS_INSTANCES dict in settings.py and make sure
        that your ZEUS_PUSH_GRADE_CALLBACK_URL is correctly set.
    """
    def _send(self, url, data=None, retries=None, **kwargs):
        retries = retries or getattr(settings, 'ZEUS_SEND_RETRIES', 3)
        assert retries > 0

        decoded_data = _json_base64_decode(data)

        command = 'curl -H "Content-Type: application/json" -X ' + \
                'POST -d \'{"compilation_output":"Q1BQ"}\' %s' % \
                decoded_data['return_url']

        print("Encoded data: ", data)
        print("Decoded data: ", decoded_data)
        print("In order to push grade (CE) for the submission sent, call: ")
        print(command)
        return 200, _json_base64_encode({'submission_id': 19123})
