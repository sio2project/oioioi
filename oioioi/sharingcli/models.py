from django.db import models


class RemoteProblemURL(models.Model):
    """Model to store the URL from which the given problem was obtained."""

    problem = models.OneToOneField(
        'problems.Problem', primary_key=True, on_delete=models.CASCADE
    )
    url = models.CharField(max_length=255)
