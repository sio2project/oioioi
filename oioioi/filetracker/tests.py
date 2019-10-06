# coding: utf-8

import datetime
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.db.models.fields.files import FieldFile, FileField

from filetracker.client import Client as FiletrackerClient
from filetracker.client.dummy import DummyClient

from oioioi.base.tests import TestCase
from oioioi.filetracker.models import FileTestModel
from oioioi.filetracker.storage import FiletrackerStorage
from oioioi.filetracker.utils import (django_to_filetracker_path,
                                      filetracker_to_django_file,
                                      make_content_disposition_header)


class TestFileField(TestCase):
    def test_file_field(self):
        f = ContentFile(b'eloziom', name='foo')

        model = FileTestModel()
        model.file_field = f
        model.save()
        pk = model.pk

        # Here the model is removed from Django's cache, so the query
        # below actually hits the database.
        del model

        model = FileTestModel.objects.get(pk=pk)
        self.assertEqual(model.file_field.read(), b'eloziom')

        model.file_field.delete()

    def test_filetracker_to_django_field(self):
        data = b'eloziom'
        path = 'my/path'
        abspath = '/' + path

        storage = default_storage
        try:
            self.assertEqual(storage.save(path, ContentFile(data)), path)

            model = FileTestModel()
            # File field is ignoring preferred name, as we can't copy file
            # in filetracker to another location
            with self.assertRaises(NotImplementedError):
                model.file_field.save('xx',
                        filetracker_to_django_file(abspath, storage))

            model.file_field = filetracker_to_django_file(abspath, storage)
            model.save()
            self.assertEqual(model.file_field.name, path)
            pk = model.pk

            # Here the model is removed from Django's cache, so the query
            # below actually hits the database.
            del model

            model = FileTestModel.objects.get(pk=pk)
            self.assertEqual(model.file_field.name, path)
            self.assertEqual(django_to_filetracker_path(model.file_field),
                                abspath)
            self.assertEqual(model.file_field.read(), data)
        finally:
            default_storage.delete(path)

    def test_django_to_filetracker_path(self):
        storage = FiletrackerStorage(prefix='/foo', client=DummyClient())
        field = FileField(storage=storage)
        value = FieldFile(None, field, 'bar')
        self.assertEqual(django_to_filetracker_path(value), '/foo/bar')

        with self.assertRaises(ValueError):
            django_to_filetracker_path(ContentFile('whatever', name='gizmo'))

        self.assertEqual('/foo/bar', django_to_filetracker_path(
                filetracker_to_django_file('/foo/bar', storage=storage)))


class TestFileStorage(TestCase):
    def _test_file_storage(self, storage):
        data = b'eloziom'
        path = 'my/path'

        with self.assertRaises(ValueError):
            storage.save('/absolute/path', ContentFile(data))

        storage.save(path, ContentFile(data))
        t = datetime.datetime.now()
        self.assertTrue(storage.exists(path))
        self.assertEqual(storage.open(path, 'rb').read(), data)
        self.assertEqual(storage.size(path), len(data))

        ctime = storage.created_time(path)
        self.assertLessEqual(ctime, t)
        self.assertGreater(ctime, t - datetime.timedelta(seconds=30))

        storage.delete(path)
        self.assertFalse(storage.exists(path))
        with self.assertRaises(Exception):
            storage.open(path, 'rb')

    def test_dummy_file_storage(self):
        storage = FiletrackerStorage()
        self._test_file_storage(storage)

    def test_real_file_storage(self):
        dir = tempfile.mkdtemp()
        try:
            client = FiletrackerClient(cache_dir=dir, remote_store=None)
            storage = FiletrackerStorage(client=client)
            self._test_file_storage(storage)
        finally:
            shutil.rmtree(dir)


class TestStreamingMixin(object):
    def assertStreamingEqual(self, response, content):
        self.assertEqual(self.streamingContent(response), content)

    def streamingContent(self, response):
        self.assertTrue(response.streaming)
        return b''.join(response.streaming_content)


class TestFileStorageViews(TestCase, TestStreamingMixin):
    fixtures = ['test_users']

    def test_raw_file_view(self):
        filename = 'tests/test_raw_file_view.txt'
        content = b'foo'
        default_storage.save(filename, ContentFile(content))
        try:
            url = reverse('raw_file', kwargs={'filename': filename})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertTrue(self.client.login(username='test_user'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertTrue(self.client.login(username='test_admin'))
            response = self.client.get(url)
            self.assertStreamingEqual(response, content)
        finally:
            default_storage.delete(filename)


class TestFileFixtures(TestCase):
    fixtures = ['test_file_field']

    def test_file_fixtures(self):
        instance = FileTestModel.objects.get()
        self.assertEqual(instance.file_field.name, 'tests/test_file_field.txt')
        self.assertEqual(instance.file_field.read(), 'whatever\x01\xff')


class TestFileUtils(TestCase):
    def test_content_disposition(self):
        value = make_content_disposition_header('inline', u'EURO rates.txt')
        self.assertIn('inline', value)
        self.assertIn('EURO rates', value)
        self.assertNotIn('filename*', value)

        value = make_content_disposition_header('inline', u'"EURO" rates.txt')
        self.assertIn(r'filename="\"EURO\" rates.txt"', value)

        value = make_content_disposition_header('attachment', u'€ rates.txt')
        self.assertEqual(value.lower(),
                'attachment; filename="rates.txt"; '
                'filename*=utf-8\'\'%e2%82%ac%20rates.txt')
