from django.db import models
from oioioi.problems.models import Problem

class RemoteProblemURL(models.Model):
    """Model to store the URL from which the given problem was obtained."""
    problem = models.OneToOneField(Problem, primary_key=True)
    url = models.CharField(max_length=255)
