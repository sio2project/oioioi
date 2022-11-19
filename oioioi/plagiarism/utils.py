import os
import re
import shutil
import socket
import tempfile

import six
from django.utils.translation import gettext_lazy as _

OIOIOI_LANGUAGE_TO_MOSS = {
    "C++": "cc",
    "C": "c",
    "Python": "python",
    "Pascal": "pascal",
    "Java": "java",
}

MOSS_SUPPORTED_LANGUAGES = set(OIOIOI_LANGUAGE_TO_MOSS)


class MossException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


# Based on: https://github.com/soachishti/moss.py
class MossClient(object):
    HOSTNAME = 'moss.stanford.edu'
    PORT = 7690
    RESULT_URL_REGEX = re.compile(r"^http://moss\.stanford\.edu/results/\d+/\d+$")

    def __init__(self, userid, lang):
        self.userid = userid
        self.lang = OIOIOI_LANGUAGE_TO_MOSS[lang]
        self.files = []

    def add_file(self, filepath, name):
        self.files.append((filepath, name))

    def submit(self, query_comment=""):
        sock = socket.socket()
        try:
            sock.connect((self.HOSTNAME, self.PORT))

            prelude = (
                "moss %(userid)d\n"
                "directory %(directory_mode)d\n"
                "X %(experimental)d\n"
                "maxmatches %(maxmatches)d\n"
                "show %(show)d\n"
                "language %(language)s\n"
                % {
                    # default MOSS settings taken from the official script
                    'userid': self.userid,
                    'directory_mode': 0,
                    'experimental': 0,
                    'maxmatches': 10,
                    'show': 250,
                    'language': self.lang,
                }
            )
            sock.sendall(six.ensure_binary(prelude))
            response = sock.recv(32)
            if not response.startswith(b"yes"):
                sock.sendall(b"end\n")
                raise MossException(_("Moss rejected the query, check your user ID."))

            if not self.files:
                raise MossException(_("Can't make a query with no submissions."))
            for i, (path, name) in enumerate(self.files):
                size = os.path.getsize(path)
                message = "file %d %s %d %s\n" % (
                    i + 1,  # file id
                    self.lang,  # programming language
                    size,  # file size
                    name,  # name of the submission
                )
                sock.sendall(six.ensure_binary(message))
                with open(path, 'rb') as f:
                    if hasattr(sock, 'sendfile'):  # new in Python 3.5
                        while f.tell() != os.fstat(f.fileno()).st_size:
                            sock.sendfile(f)
                    else:
                        for chunk in iter(lambda: f.read(4096), b''):
                            sock.sendall(chunk)

            sock.sendall(six.ensure_binary("query 0 %s\n" % query_comment))

            url = sock.recv(256)
            try:
                url = six.ensure_text(url).replace('\n', '')
            except UnicodeError:
                raise MossException(_("Moss returned an invalid url."))
            if not self.RESULT_URL_REGEX.match(url):
                raise MossException(_("Moss returned an invalid url."))

            sock.sendall(b"end\n")
        except (OSError, IOError, socket.herror, socket.gaierror, socket.timeout):
            raise MossException(_("Could not connect with the MOSS."))
        finally:
            sock.close()

        return url


def submit_and_get_url(client, submission_collector):
    submission_list = submission_collector.collect_list()
    if not submission_list:
        raise MossException(_("Can't make a query with no submissions."))
    tmpdir = tempfile.mkdtemp()
    try:
        for s in submission_list:
            display_name = (
                (s.first_name[0] if s.first_name else '')
                + (s.last_name[0] if s.last_name else '')
                + str(s.user_id)
                + '_'
                + str(s.submission_id)
            )
            dest = os.path.join(tmpdir, display_name)
            submission_collector.get_submission_source(dest, s.source_file)
            client.add_file(dest, display_name)
        return client.submit()
    finally:
        shutil.rmtree(tmpdir)
