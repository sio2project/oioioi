import base64

import six
from django.core.files.base import ContentFile
from django.db.models.fields import files

from oioioi.filetracker.filename import FiletrackerFilename


class FieldFile(files.FieldFile):
    def __init__(self, instance, field, name):
        if name is not None:
            name = FiletrackerFilename(name)
        super(FieldFile, self).__init__(instance, field, name)

    def read_using_cache(self):
        """Opens a file using a cache (if it's possible)"""
        if hasattr(self.storage, 'read_using_cache'):
            return self.storage.read_using_cache(self.name)
        return self.open('rb')


class _FileDescriptor(files.FileDescriptor):
    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__)
            )
        file = instance.__dict__[self.field.name]
        if isinstance(file, str) and file == 'none':
            instance.__dict__[self.field.name] = None
        elif isinstance(file, str) and file.startswith('data:'):
            name, content = file.split(':', 2)[1:]
            if content.startswith('raw:'):
                content = str(content[4:]).encode('ascii')
            else:
                content = base64.b64decode(content)
            try:
                # We really don't want millions of the same files in the
                # Filetracker. This way we get consistency with database
                # fixtures, where importing a fixture multiple times does not
                # create multiple records.
                self.field.storage.delete(name)
            # pylint: disable=broad-except
            except Exception:
                pass
            name = self.field.storage.save(name, ContentFile(content))
            instance.__dict__[self.field.name] = name
        return files.FileDescriptor.__get__(self, instance, owner)


class FileField(files.FileField):
    """A :class:`~django.db.models.FileField` with fixtures support.

    Default value of max_length is increased from 100 to 255.

    Values of ``FileFields`` are serialized as::

      data:<filename>:<base64-encoded data>

    It is also possible to decode a more human-friendly representaion::

      data:<filename>:raw:<raw data>

    but this works only for ASCII content.
    """

    descriptor_class = _FileDescriptor
    attr_class = FieldFile

    def __init__(self, *args, **kwargs):
        # Default value max_length=100 is not sufficient.
        kwargs.setdefault('max_length', 255)
        super(FileField, self).__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if hasattr(value, 'name') and isinstance(value.name, FiletrackerFilename):
            value = value.name.versioned_name
        return super(FileField, self).get_prep_value(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        if not value:
            return 'none'
        return (
            'data:' + value.name + ':' + six.ensure_text(base64.b64encode(value.read()))
        )
