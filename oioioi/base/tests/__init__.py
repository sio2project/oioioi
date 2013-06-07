import random
import sys
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
import os.path
import re
import tempfile
import shutil
from contextlib import contextmanager
import threading
import urllib
import subprocess

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core import mail
from django.core.files.uploadedfile import TemporaryUploadedFile, \
        SimpleUploadedFile
from django.utils import unittest
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.template import Context, Template
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from oioioi.base import utils
from oioioi.base.permissions import is_superuser, Condition, make_condition, \
    make_request_condition, RequestBasedCondition, enforce_condition
from oioioi.base.utils import RegisteredSubclassesBase, archive
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.base.fields import DottedNameField, EnumRegistry, EnumField
from oioioi.base.menu import menu_registry, OrderedRegistry, \
    side_pane_menus_registry, MenuRegistry
from oioioi.contests.utils import is_contest_admin


if not getattr(settings, 'TESTS', False):
    print >> sys.stderr, 'The tests are not using the required test ' \
            'settings from test_settings.py.'
    print >> sys.stderr, 'Make sure the tests are run ' \
            'using \'python setup.py test\' or ' \
            '\'DJANGO_SETTINGS_MODULE=oioioi.test_settings python ' \
            'manage.py test\'.'
    sys.exit(1)

basedir = os.path.dirname(__file__)


def check_not_accessible(testcase, url_or_viewname, qs=None, *args, **kwargs):
    data = kwargs.pop('data', {})
    if url_or_viewname.startswith('/'):
        url = url_or_viewname
        assert not args
        assert not kwargs
    else:
        url = reverse(url_or_viewname, *args, **kwargs)
    if qs:
        url += '?' + urllib.urlencode(qs)
    response = testcase.client.get(url, data=data, follow=True)
    testcase.assertIn(response.status_code, (403, 404, 200))
    if response.status_code == 200:
        testcase.assertIn('/login/', repr(response.redirect_chain))


def check_ajax_not_accessible(testcase, url_or_viewname, *args, **kwargs):
    data = kwargs.pop('data', {})
    if url_or_viewname.startswith('/'):
        url = url_or_viewname
        assert not args
        assert not kwargs
    else:
        url = reverse(url_or_viewname, *args, **kwargs)
    response = testcase.client.get(url, data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    testcase.assertIn(response.status_code, (403, 404))


class IgnorePasswordAuthBackend(object):
    """An authentication backend which accepts any password for an existing
       user.

       It's configured in ``settings_test.py`` and available for all tests.
    """
    supports_authentication = True
    description = _("Testing backend")

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


class FakeTimeMiddleware(object):
    _fake_timestamp = threading.local()

    def process_request(self, request):
        if not hasattr(request, 'timestamp'):
            raise ImproperlyConfigured("FakeTimeMiddleware must go after "
                    "TimestampingMiddleware")
        fake_timestamp = getattr(self._fake_timestamp, 'value', None)
        if fake_timestamp:
            request.timestamp = fake_timestamp


@contextmanager
def fake_time(timestamp):
    """A context manager which causes all requests having the specified
       timestamp, regardless of the real wall clock time."""
    FakeTimeMiddleware._fake_timestamp.value = timestamp
    yield
    del FakeTimeMiddleware._fake_timestamp.value


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

    def test_login(self):
        response = self.client.get('/', follow=True)
        self.assertNotIn('test_user', response.content)
        self.assert_(self.client.login(username='test_user'))
        response = self.client.get('/', follow=True)
        self.assertIn('test_user', response.content)
        login_url = reverse('login')
        response = self.client.get(login_url)
        self.assertEqual(302, response.status_code)
        response = self.client.get(login_url, {REDIRECT_FIELD_NAME: '/test'})
        self.assertEqual(302, response.status_code)
        self.assertTrue(response['Location'].endswith('/test'))

    def test_logout(self):
        logout_url = reverse('logout')
        response = self.client.get(logout_url)
        self.assertEqual(405, response.status_code)
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('method is not allowed', response.content)
        self.client.login(username='test_user')
        response = self.client.post(logout_url)
        self.assertEqual(200, response.status_code)
        self.assertIn('been logged out', response.content)

    def test_language_flags(self):
        response = self.client.get('/', follow=True)
        for lang_code, lang_name in settings.LANGUAGES:
            self.assertIn(lang_code + '.png', response.content)

    def test_index(self):
        self.client.login(username='test_user')
        response = self.client.get('/', follow=True)
        self.assertNotIn('navbar-login', response.content)
        self.assertNotIn('System Administration', response.content)

        self.client.login(username='test_admin')
        response = self.client.get('/', follow=True)
        self.assertNotIn('navbar-login', response.content)
        self.assertIn('System Administration', response.content)

    def test_accounts_menu(self):
        response = self.client.get('/', follow=True)
        self.assertNotIn('Change password', response.content)
        self.client.login(username='test_user')
        response = self.client.get('/', follow=True)
        self.assertIn('Change password', response.content)


class TestIndexNoContest(TestCase):
    fixtures = ('test_users',)

    def test_no_contest(self):
        response = self.client.get('/')
        self.assertIn('There are no contests available to logged out',
                response.content)
        self.client.login(username='test_admin')
        response = self.client.get('/')
        self.assertIn('This is a new OIOIOI installation',
                response.content)

    @override_settings(TEMPLATE_DIRS=(os.path.join(basedir, 'templates'),))
    def test_custom_index(self):
        response = self.client.get('/')
        self.assertIn('This is a test index template', response.content)

    def test_navbar_login(self):
        response = self.client.get('/')
        self.assertIn('navbar-login', response.content)


class TestOrderedRegistry(TestCase):
    def test_ordered_registry(self):
        reg = OrderedRegistry()
        reg.register(1, 12)
        reg.register(3)
        reg.register(2, 3)
        reg.register(4)
        self.assertListEqual([2, 1, 3, 4], list(reg))
        reg.unregister(3)
        self.assertListEqual([2, 1, 4], list(reg))
        self.assertEqual(len(reg), 3)


class TestMenu(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        self.saved_menu = menu_registry._registry
        menu_registry._registry = OrderedRegistry()

    def tearDown(self):
        menu_registry._registry = self.saved_menu

    def _render_menu(self, user=None):
        self.client.login(username=user)
        return self.client.get(reverse('index'), follow=True).content

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

    def test_menu_item_attrs_escape(self):
        menu_registry.register('test', 'Test Menu',
                lambda request: '/test_link',
                attrs={'name<>\'"&': 'value<>\'"&'})
        response = self._render_menu()
        self.assertIn('name&lt;&gt;&#39;&quot;&amp;='
                '"value&lt;&gt;&#39;&quot;&amp;"', response)

    def test_side_menus_registry(self):
        admin = User.objects.get(username='test_admin')
        user = User.objects.get(username='test_user')
        old_keys = side_pane_menus_registry.keys
        old_items = side_pane_menus_registry.items
        side_pane_menus_registry.keys = []
        side_pane_menus_registry.items = []
        try:
            side_pane_menus_registry.register(menu_registry, order=200)
            admin_menu_registry = MenuRegistry("Admin Menu", is_superuser)
            side_pane_menus_registry.register(admin_menu_registry, order=100)

            menu_registry.register('test', 'Test Menu Item',
                lambda request: '/test_menu_link', order=2)
            admin_menu_registry.register('test_admin', 'Test Admin Item',
                lambda request: '/spam', order=100)

            response = self._render_menu(user=user)
            self.assertIn('/menu/menu-icon', response)
            self.assertNotIn('User Menu', response)
            self.assertNotIn('Admin Menu', response)

            response = self._render_menu(user=admin)
            self.assertNotIn('/menu/menu-icon', response)
            self.assertIn('User Menu', response)
            self.assertIn('Admin Menu', response)
            self.assertLess(response.index('Test Admin Item'),
                    response.index('Test Menu Item'))
        finally:
            side_pane_menus_registry.keys = old_keys
            side_pane_menus_registry.items = old_items


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

        class Mixin3(object):
            name = 'mixin3'

        class Base(utils.ObjectWithMixins):
            mixins = [Mixin1]

        class Derived1(Base):
            mixins = [Mixin2]

        class Derived2(Base):
            mixins = [Mixin2]
            allow_too_late_mixins = True
            name = 'derived2'

        class Derived3(Base):
            def __init__(self, foo):
                self.name = 'derived3'
                self.foo = foo
        Derived3.mix_in(Mixin2)

        class Derived4(Base):
            name = 'derived4'
        self.assertEqual(Base().name, 'mixin1')
        self.assertEqual(Derived1().name, 'mixin2')
        self.assertEqual(Derived2().name, 'mixin2')
        self.assertEqual(Derived3(foo='bar').name, 'derived3')
        self.assertTrue(Derived2().has_mixin1)
        self.assertEqual(Derived4().name, 'derived4')

        Derived2.mix_in(Mixin3)
        with self.assertRaises(AssertionError):
            Derived1.mix_in(Mixin3)

    def test_registered_with_mixing(self):
        class Base(utils.ObjectWithMixins, utils.RegisteredSubclassesBase):
            spam = 'spam'

        class Derived(Base):
            derived = 'spam'

        class BaseMixin(object):
            basemixin = 'spam'

        class DerivedMixin(object):
            derivedmixin = 'spam'

        Derived.mix_in(DerivedMixin)
        Base.mix_in(BaseMixin)

        self.assertEquals(Derived().derivedmixin, 'spam')
        self.assertEquals(Derived().basemixin, 'spam')
        with self.assertRaises(AttributeError):
            Base().derivedmixin == 'spam'

        self.assertListEqual(Base.subclasses, [Base, Derived])
        self.assertListEqual(Derived.subclasses, [Derived])

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
        with self.assertRaises(ImportError):
            utils.get_object_by_dotted_name('oioioi.base.nonexistent.Foo')

    def test_utils_dont_need_settings(self):
        subprocess_env = os.environ.copy()
        subprocess_env.pop('DJANGO_SETTINGS_MODULE', None)
        subprocess_code = """
import sys
import oioioi.base.utils
if 'oioioi.default_settings' in sys.modules:
    sys.exit(1)
else:
    sys.exit(0)"""
        ret = subprocess.call([sys.executable, '-c', subprocess_code],
              env=subprocess_env)
        self.assertEqual(ret, 0)


class TestAllWithPrefix(unittest.TestCase):
    def test_all_with_prefix(self):
        t = Template('{% load all_with_prefix %}{% all_with_prefix a_ %}')
        context = Context(dict(a_foo='foo', a_bar='bar', b_baz='baz'))
        rendered = t.render(context)
        self.assertIn('foo', rendered)
        self.assertIn('bar', rendered)
        self.assertNotIn('baz', rendered)


class TestDottedFieldClass(RegisteredSubclassesBase):
    modules_with_subclasses = ['tests.test_dotted_field_classes']
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
        if 'oioioi.base.tests.test_dotted_field_classes' in sys.modules:
            # Well, it must have been already loaded by
            # TestDottedFieldClass.load_subclasses...
            return
        TestDottedFieldClass.load_subclasses()
        self.assertIn('oioioi.base.tests.test_dotted_field_classes',
                sys.modules)

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
        execute('exit 12', errors_to_ignore=(12, 15, 16))
        execute('exit 15', errors_to_ignore=(12, 15, 16))
        with self.assertRaises(ExecuteError):
            execute('return 14')

    def test_line_splitting(self):
        self.assertListEqual(['foo', 'lol'],
                             execute('echo "foo\nlol"', split_lines=True))

    def test_env(self):
        self.assertEqual('bar\n', execute('echo $foo', env={'foo': 'bar'}))

    def test_cwd(self):
        self.assertEqual(execute(['cat', os.path.basename(__file__)],
                cwd=os.path.dirname(__file__)), open(__file__, 'rb').read())


class TestMisc(unittest.TestCase):
    def test_reload_settings_for_coverage(self):
        import oioioi.test_settings
        reload(oioioi.test_settings)
        import oioioi.default_settings
        reload(oioioi.default_settings)

    def test_uploaded_file_name(self):
        tmp_file = TemporaryUploadedFile('whatever',
                'application/octet-stream', 0, 'utf-8')
        with utils.uploaded_file_name(tmp_file) as name:
            self.assertEquals(name, tmp_file.file.name)
        mem_file = SimpleUploadedFile('whatever', 'hello42')
        with utils.uploaded_file_name(mem_file) as name:
            self.assertTrue(name.endswith('whatever'))
            self.assertEqual(open(name, 'rb').read(), 'hello42')
        self.assertFalse(os.path.exists(name))

    def test_make_html_links(self):
        test = [('url1', 'name1'), ('url2', 'name2')]
        links = utils.make_html_links(test)
        self.assertEqual(len(links.split(' | ')), 2)
        self.assertIn('url1', links)
        self.assertIn('name1', links)
        self.assertIn('url2', links)
        self.assertIn('name2', links)


class TestRegistration(TestCase):
    def test_registration_form_fields(self):
        response = self.client.get(reverse('registration_register'))
        form = response.context['form']
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)

    def test_registration(self):
        self.client.post(reverse('registration_register'), {
            'username': 'test_foo',
            'first_name': 'Foo',
            'last_name': 'Bar',
            'email': 'foo@bar.com',
            'password1': 'xxx',
            'password2': 'xxx',
        })
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        del mail.outbox
        self.assertEqual(list(message.to), ['foo@bar.com'])
        url = re.search('^http://[^/]*(/.*)$', message.body, re.M).group(1)

        # Try to activate
        self.client.get(url)
        user = User.objects.get(username='test_foo')
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, 'Foo')
        self.assertEqual(user.last_name, 'Bar')


class TestArchive(unittest.TestCase):
    def test_archive(self):
        tmpdir = tempfile.mkdtemp()
        a = os.path.join(tmpdir, 'a')
        try:
            basedir = os.path.join(os.path.dirname(__file__), 'files')
            for good_file in ['archive.tgz', 'archive.zip']:
                filename = os.path.join(basedir, good_file)
                archive.extract(filename, tmpdir)
                self.assertTrue(os.path.exists(a))
                self.assertEqual(open(a, 'rb').read().strip(), 'foo')
                os.unlink(a)
                self.assertEqual(archive.Archive(filename).filenames(), ['a'])
            for bad_file in ['archive-with-symlink.tgz',
                    'archive-with-hardlink.tgz']:
                with self.assertRaises(archive.UnsafeArchive):
                    archive.extract(os.path.join(basedir, bad_file), tmpdir)
        finally:
            shutil.rmtree(tmpdir)


class TestAdmin(TestCase):
    fixtures = ['test_users']

    def test_admin_delete(self):
        self.client.login(username='test_admin')
        user = User.objects.get(username='test_user')
        url = reverse('oioioiadmin:auth_user_delete', args=(user.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('User: test_user', response.content)
        self.assertIn('central-well', response.content)
        response = self.client.post(url, {'post': 'yes'}, follow=True)
        self.assertIn('was deleted successfully', response.content)
        self.assertEqual(User.objects.filter(username='test_user').count(), 0)


class TestBaseViews(TestCase):
    fixtures = ['test_users']

    def test_edit_profile(self):
        self.client.login(username='test_user')
        user = User.objects.get(username='test_user')
        url = reverse('edit_profile')
        response = self.client.get(url)
        self.assertIn('registration/registration_form.html',
                [t.name for t in response.templates])
        self.assertEqual(response.context['form'].instance, user)

        data = {'username': 'test_user', 'first_name': 'fn',
                'last_name': 'ln', 'email': 'foo@bar.com'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='test_user').count(), 1)
        user = User.objects.get(username='test_user')
        self.assertEqual(user.first_name, 'fn')
        self.assertEqual(user.last_name, 'ln')
        self.assertEqual(user.email, 'foo@bar.com')

    def test_username_change_attempt(self):
        url = reverse('edit_profile')
        data = {'username': 'changed_user', 'first_name': 'fn',
                'last_name': 'ln', 'email': 'foo@bar.com'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='changed_user')
                .count(), 0)
        self.assertEqual(User.objects.filter(username='test_user').count(), 1)


class TestBackendMiddleware(TestCase):
    fixtures = ['test_users']

    def test_backend_middleware(self):
        self.client.login(username='test_user')
        response = self.client.get(reverse('index'))
        self.assertEquals('test_user', response.context['user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['user'].backend)


class TestCondition(TestCase):
    fixtures = ['test_users']

    def _fake_request_factory(self):
        factory = RequestFactory()

        def get_request():
            request = factory.request()
            request.user = AnonymousUser()
            return request

        return get_request

    def setUp(self):
        self.alwaysTrue = Condition(lambda x: True)
        self.alwaysFalse = Condition(lambda x: False)
        self.returnArg = Condition(lambda x: x)
        self.factory = self._fake_request_factory()

    def test_and_operator(self):
        true_and_true = self.alwaysTrue & self.alwaysTrue
        true_and_false = self.alwaysTrue & self.alwaysFalse
        true_and_arg = self.alwaysTrue & self.returnArg

        self.assertTrue(true_and_true(1))
        self.assertFalse(true_and_false(1))
        self.assertTrue(true_and_arg(True))
        self.assertFalse(true_and_arg(False))

    def test_or_operator(self):
        true_or_true = self.alwaysTrue | self.alwaysTrue
        true_or_false = self.alwaysTrue | self.alwaysFalse
        false_or_arg = self.alwaysFalse | self.returnArg

        self.assertTrue(true_or_true(1))
        self.assertTrue(true_or_false(1))
        self.assertTrue(false_or_arg(True))
        self.assertFalse(false_or_arg(False))

    def test_inverse_operator(self):
        not_true = ~self.alwaysTrue
        not_false = ~self.alwaysFalse
        not_arg = ~self.returnArg

        self.assertFalse(not_true(1))
        self.assertTrue(not_false(1))
        self.assertTrue(not_arg(False))
        self.assertFalse(not_arg(True))

    def test_make_condition(self):
        @make_condition()
        def otherReturnArg(arg):
            return arg

        self.assertTrue(isinstance(otherReturnArg, Condition))
        self.assertTrue(otherReturnArg(True))
        self.assertFalse(otherReturnArg(False))

    def test_request_condition(self):
        @make_request_condition
        def requestReturnArg(request):
            return request

        self.assertTrue(isinstance(requestReturnArg, RequestBasedCondition))
        self.assertTrue(requestReturnArg(True))
        self.assertFalse(requestReturnArg(False))
        # Test not throwing exception with too many arguments
        self.assertTrue(requestReturnArg(True, 1))

    def test_enforce_condition_success(self):
        @enforce_condition(self.alwaysTrue)
        def example_view(request):
            return 314

        self.assertEqual(314, example_view(1))

    def test_enforce_condition_failure_with_template(self):
        @enforce_condition(self.alwaysFalse, 'base.html')
        def example_view(request):
            pass

        res = example_view(1)
        self.assertTrue(isinstance(res, TemplateResponse))

    def test_enforce_condition_failure_without_template(self):
        @enforce_condition(self.alwaysFalse)
        def example_view(request):
            pass

        request = self.factory()
        res = example_view(request)
        self.assertTrue(isinstance(res, HttpResponseRedirect))
