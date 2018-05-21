import mimetypes
import urllib
from wsgiref.util import FileWrapper

import six
import six.moves.urllib.parse
from django.core.files import File
from django.core.files.storage import default_storage
from django.http import StreamingHttpResponse

from oioioi.filetracker.filename import FiletrackerFilename


class FileInFiletracker(File):
    """A stub :class:`django.core.files.File` subclass for assigning existing
       Filetracker files to :class:`django.db.models.FileField`s.

       Usage::

           some_model_instance.file_field = \
                   filetracker_to_django_file('some/path')
    """
    def __init__(self, storage, name):
        File.__init__(self, None, name)
        self.storage = storage
        self._size = None

    def _get_size(self):
        if self._size is None:
            self._size = self.storage.size(self.name)
        return self._size
    size = property(_get_size, File._set_size)

    def close(self):
        pass


def django_to_filetracker_path(django_file):
    """Returns the filetracker path of a :class:`django.core.files.File`."""
    storage = getattr(django_file, 'storage', None)
    if not storage:
        raise ValueError('File of type %r is not stored in Filetracker' %
                (type(django_file),))
    name = django_file.name
    if hasattr(name, 'versioned_name'):
        name = name.versioned_name
    try:
        return storage._make_filetracker_path(name)
    except AttributeError:
        raise ValueError('File is stored in %r, not Filetracker' % (storage,))


def filetracker_to_django_file(filetracker_path, storage=None):
    """Returns a :class:`~django.core.files.File` representing an existing
       Filetracker file (usable only for assigning to a
       :class:`~django.db.models.FileField`)"""
    if storage is None:
        storage = default_storage

    prefix_len = len(storage.prefix.rstrip('/'))
    if not filetracker_path.startswith(storage.prefix) or \
            filetracker_path[prefix_len:prefix_len + 1] != '/':
        raise ValueError('Path %s is outside of storage prefix %s' %
                (filetracker_path, storage.prefix))
    return FileInFiletracker(storage,
            FiletrackerFilename(filetracker_path[prefix_len + 1:]))


def make_content_disposition_header(disposition, filename):
    """Returns a Content-Disposition header field per RFC 6266.

       The ``disposition`` argument should be either ``inline`` or
       ``attachment`` and the filename should be a unicode object,
       which need not be sanitized.
    """
    disposition = disposition.lower()
    assert disposition in ('attachment', 'inline')

    # https://tools.ietf.org/html/rfc2616#section-2.2
    ascii_name = filename.encode('ascii', 'ignore').strip()
    quoted_name = ascii_name.replace(b'"', b'\\"')
    header = '%s; filename="%s"' % (disposition, quoted_name)

    utf8_name = filename.encode('utf-8', 'ignore').strip()
    if utf8_name != ascii_name:
        # https://tools.ietf.org/html/rfc5987#section-3.2
        utf8_quoted_name = six.moves.urllib.parse.quote(utf8_name, '')
        header += '; filename*=utf-8\'\'' + utf8_quoted_name

    return header


def stream_file(django_file, name=None, showable=None):
    """Returns a :class:`HttpResponse` representing a file download.

       Optional argument ``name`` sets default filename under which
       user is prompted to save that ``django_file``.

       Some types of files, as listed below in ``showable_exts`` variable, may
       by default be displayed in browser. Other are forced to be downloaded.
       Using ``showable`` flag, default behaviour may be overriden in both
       directions.
    """
    if name is None:
        name = six.text_type(django_file.name.rsplit('/', 1)[-1])
    content_type = mimetypes.guess_type(name)[0] or \
        'application/octet-stream'
    response = StreamingHttpResponse(FileWrapper(django_file),
        content_type=content_type)
    response['Content-Length'] = django_file.size
    showable_exts = ['pdf', 'ps', 'txt']
    if showable is None:
        extension = name.rsplit('.')[-1]
        showable = extension in showable_exts
    if showable:
        disposition = 'inline'
    else:
        disposition = 'attachment'
    response['Content-Disposition'] = \
        make_content_disposition_header(disposition, name)
    return response
