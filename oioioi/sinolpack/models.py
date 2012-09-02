from django.db import models
from oioioi.problems.models import Problem, make_problem_filename
from oioioi.filetracker.fields import FileField
import yaml

class ExtraConfig(models.Model):
    """Model to store ``config.yml`` present in some Sinol packages."""
    problem = models.OneToOneField(Problem)
    config = models.TextField()

    @property
    def parsed_config(self):
        if not self.config:
            return {}
        return yaml.load(self.config)

class ExtraFile(models.Model):
    """Model to store extra files (for example ``extra.zip``) present in some
       Sinol packages."""
    problem = models.ForeignKey(Problem)
    name = models.CharField(max_length=255)
    file = FileField(upload_to=make_problem_filename)

class OriginalPackage(models.Model):
    problem = models.ForeignKey(Problem)
    package_file = FileField(upload_to=make_problem_filename)
