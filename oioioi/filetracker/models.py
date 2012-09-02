from django.conf import settings
from django.db import models
from oioioi.filetracker.fields import FileField

if getattr(settings, 'TESTS', False):
    class TestFileModel(models.Model):
        file_field = FileField(upload_to='tests')
