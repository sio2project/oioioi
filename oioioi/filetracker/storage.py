import datetime
import os
import os.path
import tempfile
import warnings

import six

from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils import timezone
from oioioi.filetracker.client import get_client
from oioioi.filetracker.filename import FiletrackerFilename
from oioioi.filetracker.utils import FileInFiletracker


class FiletrackerStorage(Storage):
    def __init__(self, prefix='/', client=None):
        if client is None:
            client = get_client()
        assert prefix.startswith(
            '/'
        ), 'FiletrackerStorage.__init__ prefix must start with /'
        self.client = client
        self.prefix = prefix

    def _make_filetracker_path(self, name):
        if isinstance(name, FiletrackerFilename):
            name = name.versioned_name
        name = os.path.normcase(os.path.normpath(name))
        if os.path.isabs(name):
            raise ValueError('FiletrackerStorage does not support absolute ' 'paths')
        return os.path.join(self.prefix, name).replace(os.sep, '/')

    def _cut_prefix(self, path):
        assert path.startswith(
            self.prefix
        ), 'Path passed to _cut_prefix does not start with prefix'
        path = path[len(self.prefix) :]
        if path.startswith('/'):
            path = path[1:]
        return path

    def _open(self, name, mode):
        if 'w' in mode or '+' in mode or 'a' in mode:
            raise ValueError(
                'FiletrackerStorage.open does not support '
                'writing. Use FiletrackerStorage.save.'
            )
        path = self._make_filetracker_path(name)
        reader, _version = self.client.get_stream(path)
        return File(reader, FiletrackerFilename(name))

    def _save(self, name, content):
        path = self._make_filetracker_path(name)
        if hasattr(content, 'temporary_file_path'):
            filename = content.temporary_file_path()
        elif (
            getattr(content, 'file', None)
            and hasattr(content.file, 'name')
            and os.path.isfile(content.file.name)
        ):
            filename = content.file.name
        elif isinstance(content, FileInFiletracker):
            # This happens when file_field.save(path, file) is called
            # explicitly
            return content.name
        else:
            f = tempfile.NamedTemporaryFile()
            for chunk in content.chunks():
                if six.PY3 and isinstance(chunk, str):
                    chunk = chunk.encode('utf-8')
                f.write(chunk)
            f.flush()
            filename = f.name
        # If there will be only local store, filetracker will ignore
        # 'to_local_store' argument.
        name = self._cut_prefix(
            self.client.put_file(path, filename, to_local_store=False)
        )
        name = FiletrackerFilename(name)
        content.close()
        return name

    def read_using_cache(self, name):
        """Opens a file using a cache (if it's possible)"""
        path = self._make_filetracker_path(name)
        reader, _version = self.client.get_stream(path, serve_from_cache=True)
        return File(reader, FiletrackerFilename(name))

    # FIXME: max_length might not be implemented properly. It's guaranteed that we won't return
    # a name exceeding max_length, but we might fail to generate short name even if it's possible.
    def save(self, name, content, max_length=None):
        # Well, the default Django implementation of save coerces the returned
        # value to unicode using force_text. This is not what we want, as we
        # have to preserve FiletrackerFilename.
        if name is None:
            name = content.name
        if not hasattr(content, 'chunks'):
            content = File(content)
        name = self.get_available_name(name, max_length=max_length)
        name = self._save(name, content)
        if max_length is not None and len(name) > max_length:
            raise SuspiciousFileOperation
        return name

    def delete(self, name):
        path = self._make_filetracker_path(name)
        self.client.delete_file(path)

    def exists(self, name):
        path = self._make_filetracker_path(name)
        try:
            self.client.file_version(path)
            return True
        # pylint: disable=broad-except
        except Exception:
            return False

    def size(self, name):
        path = self._make_filetracker_path(name)
        return self.client.file_size(path)

    def modified_time(self, name):
        warnings.warn(
            """The old, non-timezone-aware methods accessed_time(), created_time(), and modified_time() are deprecated in favor of the new get_*_time() methods.
                https://docs.djangoproject.com/en/1.10/releases/1.10/#non-timezone-aware-storage-api""",
            category=DeprecationWarning,
            stacklevel=2,
        )
        path = self._make_filetracker_path(name)
        return datetime.datetime.fromtimestamp(self.client.file_version(path))

    def created_time(self, name):
        return self.modified_time(name)

    def accessed_time(self, name):
        return self.modified_time(name)

    def get_modified_time(self, name):
        path = self._make_filetracker_path(name)
        tz = timezone.get_current_timezone()
        return datetime.datetime.fromtimestamp(self.client.file_version(path), tz=tz)

    def get_created_time(self, name):
        return self.get_modified_time(name)

    def get_accessed_time(self, name):
        return self.get_modified_time(name)

    def url(self, name):
        if isinstance(name, FiletrackerFilename):
            name = name.versioned_name
        return reverse('raw_file', kwargs={'filename': name})

    def path(self, name):
        raise NotImplementedError(
            "File is in Filetracker, cannot get its local path"
        )

    def listdir(self, path):
        raise NotImplementedError("Filetracker doesn't provide path listing")
