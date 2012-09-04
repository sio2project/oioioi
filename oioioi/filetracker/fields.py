from django.core.files.base import ContentFile
from django.db.models.fields import files
from django.utils.text import get_valid_filename
from django.utils.translation import ugettext as _
from south.modelsinspector import add_introspection_rules
import base64

class _FileDescriptor(files.FileDescriptor):
    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__))
        file = instance.__dict__[self.field.name]
        if isinstance(file, basestring) and file.startswith('data:'):
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

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return 'data:' + value.name + ':' + base64.b64encode(value.read())

add_introspection_rules([], ["^oioioi\.filetracker\.fields\.FileField"])
