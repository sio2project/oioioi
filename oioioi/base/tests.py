from django.conf import settings
from django.utils import unittest
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django import forms
from django.template import Context, Template, RequestContext
from django.template.loader import render_to_string
from django.forms import ValidationError

from oioioi.base import utils
from oioioi.base.utils import RegisteredSubclassesBase
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.base.fields import DottedNameField, EnumRegistry, EnumField
from oioioi.base.menu import menu_registry, is_contest_admin, \
        MenuRegistry
from oioioi.base import menu

import random
import sys
import os.path

class IgnorePasswordAuthBackend(object):
    """An authentication backend which accepts any password for an existing
       user.

       It's configured in ``settings_test.py`` and available for all tests.
    """

    def authenticate(self, username=None, password=None):
        if not username:
            return None
        if password:
            return None
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise AssertionError('Tried to log in as %r without password, '
                    'but such a user does not exist. Probably the test '
                    'forgot to import a database fixture.' % (username,))

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class TestTestConfig(unittest.TestCase):
    def test_test_config(self):
        if not getattr(settings, 'TESTS', False):
            self.fail('The tests are not using the required test settings '
                    'from test_settings.py. Make sure the tests are run '
                    'using \'python setup.py test\' or '
                    '\'DJANGO_SETTINGS_MODULE=oioioi.test_settings python '
                    'manage.py test\'.')

class TestPermsTemplateTags(TestCase):
    fixtures = ('test_users',)

    def test_check_perms(self):
        admin = User.objects.get(username='test_admin')
        user = User.objects.get(username='test_user')
        template = Template(
                '{% load check_perm %}'
                '{% check_perm "auth.add_user" for "whatever" as p %}'
                '{% if p %}yes{% endif %}')
        self.assertEqual(template.render(Context(dict(user=admin))), 'yes')
        self.assertEqual(template.render(Context(dict(user=user))), '')

class TestIndex(TestCase):
    fixtures = ('test_users', 'test_contest')

    def setUp(self):
        self.client = Client()

    def test_login(self):
        response = self.client.get('/')
        self.assertNotIn('test_user', response.content)
        self.assert_(self.client.login(username='test_user'))
        response = self.client.get('/')
        self.assertIn('test_user', response.content)

    def test_language_flags(self):
        response = self.client.get('/')
        for lang_code, lang_name in settings.LANGUAGES:
            self.assertIn(lang_code + '.png', response.content)

    def test_index(self):
        response = self.client.get('/')
        self.assertIn('navbar-login', response.content)

        self.client.login(username='test_user')
        response = self.client.get('/')
        self.assertNotIn('navbar-login', response.content)
        self.assertNotIn('<h1>Admin</h1>', response.content)

        self.client.login(username='test_admin')
        response = self.client.get('/')
        self.assertNotIn('navbar-login', response.content)
        self.assertIn('<h1>Admin</h1>', response.content)

class TestNoContest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_no_contest(self):
        response = self.client.get('/')
        self.assertIn('This is a new OIOIOI installation', response.content)

class TestMenu(TestCase):
    fixtures = ('test_users',)

    def setUp(self):
        self.factory = RequestFactory()
        self.saved_menu = menu.menu_registry.items
        menu.menu_registry.items = []

    def tearDown(self):
        menu.menu_registry.items = self.saved_menu

    def _render_menu(self, user=None):
        request = self.factory.get('/')
        request.user = user or AnonymousUser()
        request.contest = None
        return render_to_string('base-with-menu.html',
                context_instance=RequestContext(request))

    def test_menu(self):
        menu_registry.register('test2', 'Test Menu Item 2',
                lambda request: '/test_menu_link2', order=2)
        menu_registry.register('test1', 'Test Menu Item 1',
                lambda request: '/test_menu_link1', order=1)
        response = self._render_menu()
        self.assertIn('Test Menu Item 1', response)
        self.assertIn('Test Menu Item 2', response)
        self.assertIn('/test_menu_link1', response)
        self.assertIn('/test_menu_link2', response)
        self.assertLess(response.index('Test Menu Item 1'),
                response.index('Test Menu Item 2'))

    def test_is_contest_admin(self):
        admin = User.objects.get(username='test_admin')
        user = User.objects.get(username='test_user')
        menu_registry.register('test', 'Test Admin Menu',
                lambda request: '/test_admin_link',
                condition=is_contest_admin)
        response = self._render_menu(user=admin)
        self.assertIn('test_admin_link', response)
        response = self._render_menu(user=user)
        self.assertNotIn('test_admin_link', response)

class TestUtils(unittest.TestCase):
    def test_classinit(self):
        TestUtils.classinit_called_counter = 0
        try:
            class C(utils.ClassInitBase):
                @classmethod
                def __classinit__(cls):
                    TestUtils.classinit_called_counter += 1
            self.assertEqual(TestUtils.classinit_called_counter, 1)
            class D(C):
                pass
            self.assertEqual(TestUtils.classinit_called_counter, 2)
        finally:
            del TestUtils.classinit_called_counter

    def test_registered_subclasses_meta(self):
        class C(utils.RegisteredSubclassesBase):
            abstract = True
        self.assertEqual(C.subclasses, [])
        class C1(C):
            pass
        self.assertIn(C1, C.subclasses)
        class C2(C1):
            pass
        self.assertIn(C2, C.subclasses)
        self.assertIn(C2, C1.subclasses)

        class D(utils.RegisteredSubclassesBase):
            pass
        self.assertEqual(D.subclasses, [D])
        self.assertEqual(len(C.subclasses), 2)

    def test_object_with_mixins(self):
        class Mixin1(object):
            name = 'mixin1'
            has_mixin1 = True
        class Mixin2(object):
            name = 'mixin2'
        class Base(utils.ObjectWithMixins):
            mixins = [Mixin1]
        class Derived1(Base):
            mixins = [Mixin2]
        class Derived2(Base):
            mixins = [Mixin2]
            name = 'derived2'
        class Derived3(Base):
            def __init__(self, foo):
                self.name = 'derived3'
                self.foo = foo
        Derived3.mix_in(Mixin2)
        self.assertEqual(Base().name, 'mixin1')
        self.assertEqual(Derived1().name, 'mixin2')
        self.assertEqual(Derived2().name, 'mixin2')
        self.assertEqual(Derived3(foo='bar').name, 'derived3')
        self.assertTrue(Derived2().has_mixin1)

    def test_memoized(self):
        memoized_random = utils.memoized(random.random)
        self.assertEqual(memoized_random(), memoized_random())
        memoized_randbits = utils.memoized(random.getrandbits)
        self.assertNotEqual(memoized_randbits(64), memoized_randbits(63))

    def test_reset_memoized(self):
        memoized_random = utils.memoized(random.random)
        r1 = memoized_random()
        utils.reset_memoized(memoized_random)
        r2 = memoized_random()
        self.assertNotEqual(r1, r2)

    def test_get_object_by_dotted_name(self):
        self.assert_(utils.get_object_by_dotted_name(
            'oioioi.base.tests.TestUtils') is TestUtils)
        with self.assertRaises(AssertionError):
            utils.get_object_by_dotted_name('TestUtils')
        with self.assertRaisesRegexp(ImportError, 'object .* not found'):
            utils.get_object_by_dotted_name('oioioi.base.tests.Nonexistent')
        with self.assertRaisesRegexp(ImportError, 'object .* not found'):
            utils.get_object_by_dotted_name('oioioi.base.nonexistent.Foo')

class TestAllWithPrefix(unittest.TestCase):
    def test_all_with_prefix(self):
        t = Template('{% load all_with_prefix %}{% all_with_prefix a_ %}')
        context = Context(dict(a_foo='foo', a_bar='bar', b_baz='baz'))
        rendered = t.render(context)
        self.assertIn('foo', rendered)
        self.assertIn('bar', rendered)
        self.assertNotIn('baz', rendered)

class TestDottedFieldClass(RegisteredSubclassesBase):
    modules_with_subclasses = ['test_dotted_field_classes']
    abstract = True

class TestDottedFieldSubclass(TestDottedFieldClass):
    description = 'Description'

class TestFields(unittest.TestCase):
    def test_dotted_name_field(self):
        field = DottedNameField('oioioi.base.tests.TestDottedFieldClass')
        field.validate('oioioi.base.tests.TestDottedFieldSubclass', None)
        with self.assertRaises(ValidationError):
            field.validate('something.stupid', None)
        with self.assertRaises(ValidationError):
            field.validate('oioioi.base.tests.TestDottedFieldClass', None)
        self.assertEqual(list(field.choices),
                [('oioioi.base.tests.TestDottedFieldSubclass',
                    TestDottedFieldSubclass.description)])

    def test_dotted_name_field_module_loading(self):
        if 'oioioi.base.test_dotted_field_classes' in sys.modules:
            del sys.modules['oioioi.base.test_dotted_field_classes']
        TestDottedFieldClass.load_subclasses()
        self.assertIn('oioioi.base.test_dotted_field_classes', sys.modules)

    def test_enum_field(self):
        registry = EnumRegistry()
        field = EnumField(registry)
        registry.register('OK', 'OK')
        registry.register('OK', 'Should be ignored (duplicate)')
        registry.register('ERR', 'Error')
        self.assertEqual(sorted(list(field.choices)),
                [('ERR', 'Error'), ('OK', 'OK')])
        with self.assertRaises(ValidationError):
            field.validate('FOO', None)

class TestExecute(unittest.TestCase):
    def test_echo(self):
        self.assertEqual("foo\n", execute("echo foo"))

    def test_echo_with_list_command(self):
        self.assertEqual("-n test\n", execute(['echo', '-n test']))

    def test_cat_with_string_input(self):
        input_text = 'hello there!'
        output_text = execute('cat', stdin=input_text)
        self.assertEqual(input_text, output_text)

    def test_error(self):
        with self.assertRaises(ExecuteError):
            execute('exit 12')  # random error code

    def test_ignored_error(self):
        execute('exit 12', ignore_errors=True)

    def test_ignored_error_list(self):
        execute('exit 12', errors_to_ignore=(12,15,16))
        execute('exit 15', errors_to_ignore=(12,15,16))
        with self.assertRaises(ExecuteError):
            execute('return 14')

    def test_line_splitting(self):
        self.assertListEqual(['foo', 'lol'],
                             execute('echo "foo\nlol"', split_lines=True))

    def test_env(self):
        self.assertEqual('bar\n', execute('echo $foo', env = {'foo': 'bar'}))

    def test_cwd(self):
        self.assertEqual(execute(['cat', os.path.basename(__file__)],
                cwd=os.path.dirname(__file__)), open(__file__, 'rb').read())

class TestMisc(unittest.TestCase):
    def test_reload_settings_for_coverage(self):
        import oioioi.test_settings
        reload(oioioi.test_settings)
