=============
Storing files
=============

.. _Filetracker: ../../../../sioworkers/filetracker/rst/build/html/index.html

In OIOIOI we need some mechanism to exchange files with external judging
machines. We use `Filetracker`_ for it. It's our custom module and lives in the
Git repository in ``lib/filetracker``.

Filetracker in Django
---------------------

.. _Django files docs: https://docs.djangoproject.com/en/dev/topics/files/

Most of the `Django files docs`_ still apply. The only difference is that we
use our custom model field and storage manager, as specified in ``settings.py``::

    DEFAULT_FILE_STORAGE = 'oioioi.filetracker.storage.FiletrackerStorage'

To store a field in a model, use code like this::

    from django.db import models
    from oioioi.filetracker.fields import FileField

    class TestFileModel(models.Model):
        file_field = FileField(upload_to='some/folder')

Frequently you don't want all files from a single field occupy a single folder.
No one wants all input files for all tasks to be in a single folder. Therefore
in practice you usually pass a filename generator as ``upload_to``. You may do
it like this::

    from djang.utils.text import get_valid_filename
    import os.path

    def make_test_filename(instance, filename):
        # instance will be an instance of Test
        # filename will be the name of the file uploaded by the user
        #   or passed programmatically to instance.input_file.save()
        return 'problems/%d/%s' % (instance.problem.id,
                get_valid_filename(os.path.basename(filename)))

    class Test(models.Model):
        problem = models.ForeignKey('Problem', on_delete=models.CASCADE)
        input_file = FileField(upload_to=make_test_filename)

To store an existing file, write something like this::

    from django.core.files import File
    my_model.file_field = File(open('/etc/passwd', 'rb'), name='myfile.txt')
    # or: my_model.file_field.save('myfile.txt', File(open('/etc/passwd', 'rb')))

To store a string variable::

    from django.core.files import ContentFile
    my_model.file_field = ContentFile('content of file', name='myfile.txt')
    # or: my_model.file_field.save('myfile.txt', ContentFile('content of file'))

To assign a file, which is already in Filetracker::

    from oioioi.filetracker.utils import filetracker_to_django_file
    my_model.file_field = filetracker_to_django_file('/path/in/filetracker/to/myfile.txt')

.. note:: This is assignment, so any output of ``upload_to`` will be ignored.

.. autofunction:: oioioi.filetracker.utils.filetracker_to_django_file

.. autofunction:: oioioi.filetracker.utils.django_to_filetracker_path


Accessing Filetracker client
-----------------------------

To obtain the Filetracker client class instance, use
:func:`oioioi.filetracker.client.get_client`. Our Django Filetracker storage
backend uses this function as well.

.. autofunction:: oioioi.filetracker.client.get_client

.. autofunction:: oioioi.filetracker.client.remote_storage_factory

Indeed, in ``settings.py`` you will find::

    FILETRACKER_CLIENT_FACTORY = 'oioioi.filetracker.client.remote_storage_factory'


Testing with files
------------------

.. _Database fixtures: https://docs.djangoproject.com/en/dev/howto/initial-data/

`Database fixtures`_ allow to store database entities ready for use in tests.
Our :class:`~FileField` is tweaked to also serialize its content, and deserialize
automatically when fixtures are loaded.
