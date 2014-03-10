import json

from django.test import TestCase

from oioioi.zeus.backends import _json_base64_encode, _json_base64_decode, \
                                 Base64String, ZeusServer


def ZeusTestServer(fixtures_path):
    """Parametrized class for test zeus server, returning results from
       fixtures.
    """
    class _ZeusTestServer(ZeusServer):
        def __init__(self):
            super(_ZeusTestServer, self).__init__(self)
            with open(fixtures_path) as f:
                self.fixtures = json.load(f)

        def _send(self, url, data=None, method='GET'):
            assert data is None or method == 'POST'
            matching_fixtures = [f for f in self.fixtures if f['url'] == url
                                 and f['method'] == method]
            assert len(matching_fixtures) == 1
            fix = matching_fixtures[0]
            return fix['result_code'], fix['result']
    return _ZeusTestServer


ZeusCorrectServer = ZeusTestServer(
        'oioioi/zeus/fixtures/test_zeus_correct.json')
ZeusIncorrectServer = ZeusTestServer(
        'oioioi/zeus/fixtures/test_zeus_incorrect.json')


class ZeusJsonTest(TestCase):
    def setUp(self):
        self._ob = {
            u'dict': {u'key': Base64String('somestring')},
            u'key': Base64String('string'),
        }
        self._ob_json = \
                '{"dict": {"key": "c29tZXN0cmluZw=="}, "key": "c3RyaW5n"}'

        with open('oioioi/zeus/fixtures/test_zeus_correct.json') as f:
            self._jsons = [f['result'] for f in json.load(f)]

    def test_json_base64_encode(self):
        self.assertEquals(_json_base64_encode(self._ob), self._ob_json)

    def test_json_base64_decode(self):
        self.assertEquals(self._ob, _json_base64_decode(self._ob_json))
        for j in self._jsons:
            _json_base64_decode(j)

    def test_json_base64_identity(self):
        self.assertEquals(self._ob, _json_base64_decode(
                          _json_base64_encode(self._ob)))
        self.assertEquals(self._ob_json, _json_base64_encode(
                          _json_base64_decode(self._ob_json)))
        for j in self._jsons:
            self.assertEquals(j, _json_base64_encode(_json_base64_decode(j)))
