from django.core.servers.basehttp import FileWrapper
from django.core.files.storage import default_storage
from django.core.files import File
from django.http import HttpResponse
import mimetypes

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

    def _get_size(self):
        if not hasattr(self, '_size'):
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
    try:
        return storage._make_filetracker_path(django_file.name)
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
            filetracker_path[prefix_len + 1:])

def stream_file(django_file):
    name = unicode(django_file.name.rsplit('/', 1)[-1])
    content_type = mimetypes.guess_type(name)[0] or \
        'application/octet-stream'
    response = HttpResponse(FileWrapper(django_file),
        content_type=content_type)
    response['Content-Length'] = django_file.size
    response['Content-Disposition'] = 'attachment; filename=%s' \
        % (name.encode('ascii', 'ignore'),)
    return response
