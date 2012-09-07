from django.forms.util import flatatt
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.utils.importlib import import_module
import functools
import itertools
from contextlib import contextmanager
import tempfile
import shutil
import traceback

# Metaclasses

class ClassInitMeta(type):
    """Meta class triggering __classinit__ on class intialization."""
    def __init__(cls, class_name, bases, new_attrs):
        type.__init__(cls, class_name, bases, new_attrs)
        cls.__classinit__()

class ClassInitBase(object):
    """Abstract base class injecting ClassInitMeta meta class."""

    __metaclass__ = ClassInitMeta

    @classmethod
    def __classinit__(cls):
        """
            Empty __classinit__ implementation.

            This must be a no-op as subclasses can't reliably call base class's
            __classinit__ from their __classinit__s.

            Subclasses of __classinit__ should look like:

            .. python::

                class MyClass(ClassInitBase):

                    @classmethod
                    def __classinit__(cls):
                        # Need globals().get as MyClass may be still undefined.
                        super(globals().get('MyClass', cls),
                                cls).__classinit__()
                        ...

                class Derived(MyClass):

                    @classmethod
                    def __classinit__(cls):
                        super(globals().get('Derived', cls),
                                cls).__classinit__()
                        ...
        """
        pass

class RegisteredSubclassesMeta(type):
    def __new__(cls, name, bases, dct):
        assert 'subclasses' not in dct, \
                '%s defines attribute subclasses, but has ' \
                'RegisteredSubclassesMeta metaclass'
        dct['subclasses'] = []

        # Each class must have its own 'abstract' attribute
        dct.setdefault('abstract', False)

        return type.__new__(cls, name, bases, dct)

    def __init__(cls, name, bases, new_attrs):
        type.__init__(cls, name, bases, new_attrs)

        def find_superclass(cls):
            superclasses = filter(
                    lambda c: isinstance(c, RegisteredSubclassesMeta),
                    cls.__bases__)
            if not superclasses:
                return None
            if len(superclasses) > 1:
                raise AssertionError('%s derives from more than one '
                        'RegisteredSubclassesMeta instances' % (cls.__name__,))
            return superclasses[0]

        # Add the class to all superclasses' 'subclasses' attribute, including
        # self.
        superclass = cls
        while superclass:
            if not cls.abstract:
                superclass.subclasses.append(cls)
            superclass = find_superclass(superclass)

class RegisteredSubclassesBase(object):
    """A base class for classes which should have a list of subclasses
       available.

       The list of subclasses is available in their :attr:`subclasses` class
       attributes. Classes which have *explicitly* set :attr:`abstract` class
       attribute to ``True`` are not added to :attr:`subclasses`.

       If a class has ``modules_with_subclasses`` attribute (list or string),
       then specified modules for all installed applications can be loaded by
       calling :meth:`~RegisteredSubclassesBase.load_subclasses`.
    """

    __metaclass__ = RegisteredSubclassesMeta

    _subclasses_loaded = False

    @classmethod
    def load_subclasses(cls):
        if cls._subclasses_loaded:
            return
        from django.conf import settings
        modules_to_load = getattr(cls, 'modules_with_subclasses', [])
        if isinstance(modules_to_load, basestring):
            modules_to_load = [modules_to_load]
        for app_module in list(settings.INSTALLED_APPS):
            for name in modules_to_load:
                try:
                    module = '%s.%s' % (app_module, name)
                    import_module(module)
                except ImportError:
                    continue
        cls._subclasses_loaded = True

class _RemoveMixinsFromInitMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs.pop('mixins', None)
        super(_RemoveMixinsFromInitMixin, self).__init__(*args, **kwargs)

class ObjectWithMixins(object):
    """Base class for objects which support mixins.

       Mixins are `nice tools in Python
       <http://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-are-they-useful>`_.
       But they have one drawback -- you have to specify new class' mixins at
       the point where you declare it. This class solves this problem. Mixins
       can be now be added on the fly by :meth:`~ObjectWithMixins.mix_in`
       method. This allows for a more flexible modular design.

       For example::

           # base.py
           class UserController(ObjectWithMixins):
               def render_user_info(self, user):
                   return "Login: " + user.username

           # some_external_module.py
           class UserControllerBeautifier(object):
               def render_user_info(self, user):
                   super_info = super(UserControllerBeautifier, self).render_user_info(user)
                   return '<font color="red">' + super_info + '</font>'
           UserController.mix_in(UserControllerBeautifier)

       Mixins can also be specified by providing a :attr:`mixins` class
       attribute or by passing an additional keyword argument ``mixins`` to the
       constructor.

       The actual class with all the mixins is created each time the class
       constructor is called.
    """

    #: A list of mixins to be automatically mixed in to all instances of the
    #: particular class and its subclasses.
    mixins = []

    #: Setting this to ``True`` allows adding mixins to the class after it has
    #: been instantiated. Existing instances will not have new mixins added.
    allow_too_late_mixins = False

    def __new__(cls, *args, **kwargs):
        mixin_lists = [[_RemoveMixinsFromInitMixin], kwargs.pop('mixins', [])]
        for c in cls.__mro__:
            if issubclass(c, ObjectWithMixins):
                c._has_instances = True
                if 'mixins' in c.__dict__:
                    mixin_lists.append(reversed(c.mixins))
        bases = tuple(itertools.chain(*mixin_lists)) + (cls,)
        if len(bases) > 1:
            real_cls = type(cls.__name__ + 'WithMixins', bases,
                    dict(__module__=cls.__module__))
        else:
            real_cls = cls
        real_cls.__unmixed_class__ = cls
        return object.__new__(real_cls)

    @classmethod
    def mix_in(cls, mixin):
        """Appends the given mixin to the list of class mixins."""
        assert cls.allow_too_late_mixins or \
                '_has_instances' not in cls.__dict__, \
                "Adding mixin %r to %r too late. The latter already has " \
                "instances." % (mixin, cls)
        if 'mixins' not in cls.__dict__:
            cls.mixins = []
        cls.mixins.append(mixin)

# Memoized-related bits copied from SqlAlchemy.

class memoized_property(object):   # Copied from SqlAlchemy
    """A read-only @property that is only evaluated once."""
    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result

def memoized(fn):
    """Simple wrapper that adds result caching for functions with positional
       arguments only.

       The arguments must be hashable so that they can be stored as keys in
       a dict.
    """
    cache = {}
    @functools.wraps(fn)
    def memoizer(*args):
        if args not in cache:
            cache[args] = fn(*args)
        return cache[args]
    memoizer.cache = cache
    return memoizer

def reset_memoized(memoized_fn):
    """Clear the memoization cache of a function decorated by
       :fun:`memoized`."""
    memoized_fn.cache.clear()

# Finding objects by name

@memoized
def get_object_by_dotted_name(name):
    """Returns an object by its dotted name, e.g.
       ``oioioi.base.utils.get_object_by_dotted_name``."""
    if '.' not in name:
        raise AssertionError('Invalid object name: %s' % (name,))
    module, obj = name.rsplit('.', 1)
    try:
        return getattr(__import__(module, fromlist=[obj]), obj)
    except (ImportError, AttributeError), e:
        raise ImportError('Requested object %r not found: %s' % (name, e))

# Generating HTML

def make_html_link(href, name, extra_attrs={}):
    attrs = {'href': href}
    attrs.update(extra_attrs)
    return mark_safe(u'<a %s>%s</a>' % (flatatt(attrs),
            conditional_escape(force_unicode(name))))

def make_html_links(links, extra_attrs={}):
    links = [make_html_link(href, name, extra_attrs) for href, name in links]
    return mark_safe(' | '.join(links))

# File uploads

@contextmanager
def uploaded_file_name(uploaded_file):
    if hasattr(uploaded_file, 'temporary_file_path'):
        yield uploaded_file.temporary_file_path()
    else:
        f = tempfile.NamedTemporaryFile(suffix=uploaded_file.name)
        shutil.copyfileobj(uploaded_file, f)
        f.flush()
        yield f.name
        f.close()

