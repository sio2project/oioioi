# pylint: disable=W0703
# Catching too general exception Exception
from django.core.files.base import ContentFile
from django.db.models.fields import files
from south.modelsinspector import add_introspection_rules
from oioioi.filetracker.filename import FiletrackerFilename
import base64


class FieldFile(files.FieldFile):
    def __init__(self, instance, field, name):
        if name is not None:
            name = FiletrackerFilename(name)
        super(FieldFile, self).__init__(instance, field, name)


class _FileDescriptor(files.FileDescriptor):
    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__))
        file = instance.__dict__[self.field.name]
        if isinstance(file, basestring) and file == 'none':
            instance.__dict__[self.field.name] = None
        elif isinstance(file, basestring) and file.startswith('data:'):
            name, content = file.split(':', 2)[1:]
            if content.startswith('raw:'):
                content = str(content[4:])
            else:
                content = base64.b64decode(content)
            try:
                # We really don't want millions of the same files in the
                # Filetracker. This way we get consistency with database
                # fixtures, where importing a fixture multiple times does not
                # create multiple records.
                self.field.storage.delete(name)
            except Exception:
                pass
            name = self.field.storage.save(name, ContentFile(content))
            instance.__dict__[self.field.name] = name
        return files.FileDescriptor.__get__(self, instance, owner)


class FileField(files.FileField):
    """A :class:`~django.db.models.FileField` with fixtures support.

       Values of ``FileFields`` are serialized as::

         data:<filename>:<base64-encoded data>

       It is also possible to decode a more human-friendly representaion::

         data:<filename>:raw:<raw data>

       but this works only for ASCII content.
    """

    descriptor_class = _FileDescriptor
    attr_class = FieldFile

    def get_prep_lookup(self, lookup_type, value):
        if hasattr(value, 'name') \
                and isinstance(value.name, FiletrackerFilename):
            value = value.name.versioned_name
        return super(FileField, self).get_prep_lookup(lookup_type, value)

    def get_prep_value(self, value):
        if hasattr(value, 'name') \
                and isinstance(value.name, FiletrackerFilename):
            value = value.name.versioned_name
        return super(FileField, self).get_prep_value(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        if not value:
            return 'none'
        return 'data:' + value.name + ':' + base64.b64encode(value.read())

add_introspection_rules([], [r'^oioioi\.filetracker\.fields\.FileField'])
