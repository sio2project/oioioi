from django.core.files.storage import Storage
from django.core.files import File
from django.core.urlresolvers import reverse
from oioioi.filetracker.client import get_client

import os
import os.path
import tempfile
import datetime
from oioioi.filetracker.utils import FileInFiletracker

class FiletrackerStorage(Storage):
    def __init__(self, prefix='/', client=None):
        if client is None:
            client = get_client()
        assert prefix.startswith('/'), \
                'FiletrackerStorage.__init__ prefix must start with /'
        self.client = client
        self.prefix = prefix

    def _make_filetracker_path(self, name):
        name = os.path.normcase(os.path.normpath(name))
        if os.path.isabs(name):
            raise ValueError('FiletrackerStorage does not support absolute '
                    'paths')
        return os.path.join(self.prefix, name).replace(os.sep, '/')

    def _open(self, name, mode):
        if 'w' in mode or '+' in mode or 'a' in mode:
            raise ValueError('FiletrackerStorage.open does not support '
                    'writing. Use FiletrackerStorage.save.')
        path = self._make_filetracker_path(name)
        reader, version = self.client.get_stream(path)
        return File(reader, name)

    def _save(self, name, content):
        path = self._make_filetracker_path(name)
        if hasattr(content, 'temporary_file_path'):
            filename = content.temporary_file_path()
        elif getattr(content, 'file', None) \
                and hasattr(content.file, 'name') \
                and os.path.isfile(content.file.name):
            filename = content.file.name
        elif isinstance(getattr(content, 'file', None), FileInFiletracker):
            # This happens when used with field assignment
            # We are ignoring suggested name, as copying files in filetracker
            # isn't implemented
            return content.file.name
        elif isinstance(content, FileInFiletracker):
            # This happens when file_field.save(path, file) is called explicitly
            raise NotImplementedError("Filename cannot be changed")
        else:
            f = tempfile.NamedTemporaryFile()
            for chunk in content.chunks():
                f.write(chunk)
            f.flush()
            filename = f.name
        self.client.put_file(path, filename)
        content.close()
        return name

    def delete(self, name):
        path = self._make_filetracker_path(name)
        self.client.delete_file(path)

    def exists(self, name):
        path = self._make_filetracker_path(name)
        try:
            self.client.file_version(path)
            return True
        except Exception:
            return False

    def size(self, name):
        path = self._make_filetracker_path(name)
        return self.client.file_size(path)

    def modified_time(self, name):
        path = self._make_filetracker_path(name)
        return datetime.datetime.fromtimestamp(self.client.file_version(path))

    def created_time(self, name):
        return self.modified_time(name)

    def accessed_time(self, name):
        return self.modified_time(name)

    def url(self, name):
        return reverse('oioioi.filetracker.views.raw_file_view',
                kwargs={'file_name': name})
