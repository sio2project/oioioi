from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.importlib import import_module
from django.forms import ValidationError
from south.modelsinspector import add_introspection_rules
from oioioi.base.utils import get_object_by_dotted_name

class DottedNameField(models.CharField):
    """A ``CharField`` designed to store dotted names of Python classes.

       The mandatory argument ``superclass`` should be the class, which
       subclasses can be stored in such fields.

       Possible choices are automatically provided to Django, if the superclass
       has an attribute ``subclasses`` listing possible subclasses.
       :cls:`oioioi.base.utils.RegisteredSubclassesBase` may be used to
       automatically build such an attribute.

       Before looking up subclasses, modules with names specified in the
       ``modules_with_subclasses`` class attribute of ``superclass`` are loaded
       from all applications registered with Django.

       Subclasses may define ``description``s, which will be shown to the users
       in auto-generated forms instead of dotted names.
    """

    description = _("Dotted name of some Python object")

    __metaclass__ = models.SubfieldBase

    def __init__(self, superclass, *args, **kwargs):
        kwargs['max_length'] = 255
        kwargs['choices'] = self._generate_choices()
        models.CharField.__init__(self, *args, **kwargs)

        self.superclass_name = superclass
        self._superclass = superclass

    def _get_superclass(self):
        if isinstance(self._superclass, basestring):
            self._superclass = get_object_by_dotted_name(self._superclass)
        return self._superclass

    def _generate_choices(self):
        superclass = self._get_superclass()
        superclass.load_subclasses()
        subclasses = superclass.subclasses
        if subclasses:
            for subclass in subclasses:
                dotted_name = '%s.%s' % (subclass.__module__,
                        subclass.__name__)
                human_readable_name = getattr(subclass, 'description',
                        dotted_name)
                yield dotted_name, human_readable_name

    def to_python(self, value):
        superclass = self._get_superclass()
        superclass.load_subclasses()
        return super(DottedNameField, self).to_python(value)

    def validate(self, value, model_instance):
        try:
            obj = get_object_by_dotted_name(value)
        except Exception:
            raise ValidationError(_("Object %s not found") % (value,))

        superclass = self._get_superclass()
        if not issubclass(obj, superclass):
            raise ValidationError(_("%(value)s is not a %(class_name)s")
                    % dict(value=value, class_name=superclass.__name__))

        if getattr(obj, 'abstract', False):
            raise ValidationError(_("%s is an abstract class and cannot be "
                "used") % (value,))

add_introspection_rules([
    (
        [DottedNameField],
        [],
        {
            'superclass': ['superclass_name', {}],
        }
    )
], [r'^oioioi\.base\.fields\.DottedNameField'])


class EnumRegistry(object):
    def __init__(self, max_length=64):
        self.entries = []
        self.max_length = max_length

    def register(self, value, description):
        if len(value) > self.max_length:
            raise ValueError('Enum values must not be longer than %d chars' %
                    (self.max_length,))
        if not self.entries or value not in zip(*self.entries)[0]:
            self.entries.append((value, description))

class EnumField(models.CharField):
    """A ``CharField`` designed to store a value from an extensible set.

       The set of possible values is stored in an :cls:`EnumRegistry`, which
       must be passed to the constructor.

       Other apps may then extend the set of available choices by calling
       :meth:`EnumRegistry.register`. The list of choices is populated the
       first time it is needed, therefore other application should probably
       register their values early during initialization, preferably in their
       ``models.py``.
    """

    description = _("Enumeration")

    def __init__(self, registry=None, *args, **kwargs):
        if registry:
            # This is to allow south to create this field without the need to
            # store the registry.
            assert isinstance(registry, EnumRegistry), \
                    'Invalid registry passed to EnumField.__init__: %r' % \
                    (registry,)
            kwargs['max_length'] = registry.max_length
            kwargs['choices'] = self._generate_choices()
        models.CharField.__init__(self, *args, **kwargs)
        self.registry = registry

    def _generate_choices(self):
        for item in self.registry.entries:
            yield item

add_introspection_rules([], [r'^oioioi\.base\.fields\.EnumField'])
